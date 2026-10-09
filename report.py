from datetime import datetime, timedelta
from decimal import Decimal
from math import ceil, log10

from openpyxl import Workbook
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.chart.label import DataLabelList
from openpyxl.chart.text import RichText
from openpyxl.drawing.text import (
    Paragraph,
    ParagraphProperties,
    CharacterProperties,
    Font as DrawingFont,
)
from openpyxl.styles import (
    Font,
    PatternFill,
    Alignment,
    Border,
    Side,
)
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.page import PageMargins

from analytics import get_financial_events, calculate_analytics
from database import get_connection
from config import REPORT_DIR, LOCAL_TIMEZONE


# --------------------------------------------------
# REPORT STYLING
# --------------------------------------------------

HEADER_COLOR = "17365D"
ALTERNATE_COLOR = "EAF2F8"
WHITE = "FFFFFF"
BLACK = "000000"

CURRENCY_FORMAT = '$#,##0.00;[Red]($#,##0.00)'

THIN_BLACK_BORDER = Border(
    left=Side(style="thin", color=BLACK),
    right=Side(style="thin", color=BLACK),
    top=Side(style="thin", color=BLACK),
    bottom=Side(style="thin", color=BLACK),
)


def configure_printing(ws, repeat_headers=True):
    """Configure worksheets for landscape printing."""

    ws.page_setup.orientation = "landscape"
    ws.page_setup.paperSize = ws.PAPERSIZE_LETTER

    # Fit tables to one page wide, allowing multiple pages tall.
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0

    ws.page_margins = PageMargins(
        left=0.25,
        right=0.25,
        top=0.40,
        bottom=0.40,
        header=0.15,
        footer=0.15,
    )

    ws.print_options.horizontalCentered = True
    ws.sheet_view.showGridLines = False

    if repeat_headers:
        ws.print_title_rows = "1:1"

    ws.oddFooter.center.text = "Page &P of &N"


def style_table(ws, header_row=1):
    """Apply borders, alternating colors, and readable sizing."""

    ws.freeze_panes = f"A{header_row + 1}"

    for row in ws.iter_rows(
        min_row=header_row,
        max_row=ws.max_row,
    ):
        for cell in row:
            cell.border = THIN_BLACK_BORDER

            if cell.row == header_row:
                cell.font = Font(
                    name="Aptos",
                    size=11,
                    bold=True,
                    color=WHITE,
                )
                cell.fill = PatternFill(
                    fill_type="solid",
                    fgColor=HEADER_COLOR,
                )
                cell.alignment = Alignment(
                    horizontal="center",
                    vertical="center",
                    wrap_text=True,
                )
            else:
                cell.font = Font(
                    name="Aptos",
                    size=10,
                    color=BLACK,
                )

                if (cell.row - header_row) % 2 == 0:
                    cell.fill = PatternFill(
                        fill_type="solid",
                        fgColor=ALTERNATE_COLOR,
                    )
                else:
                    cell.fill = PatternFill(
                        fill_type="solid",
                        fgColor=WHITE,
                    )

                cell.alignment = Alignment(
                    vertical="center",
                    wrap_text=True,
                )

    ws.row_dimensions[header_row].height = 30

    for row_number in range(header_row + 1, ws.max_row + 1):
        ws.row_dimensions[row_number].height = 25

    # Automatically size columns based on contents.
    for column in ws.columns:
        column_letter = get_column_letter(column[0].column)

        max_length = max(
            len(str(cell.value or ""))
            for cell in column
        )

        ws.column_dimensions[column_letter].width = min(
            max(max_length + 4, 18),
            48,
        )

    ws.auto_filter.ref = (
        f"A{header_row}:"
        f"{get_column_letter(ws.max_column)}{ws.max_row}"
    )

    configure_printing(ws)

    ws.print_area = (
        f"A1:{get_column_letter(ws.max_column)}{ws.max_row}"
    )


# --------------------------------------------------
# CHART HELPERS
# --------------------------------------------------

def set_axis_font_size(axis, size=14):
    """Increase chart axis tick-label font size."""

    character_properties = CharacterProperties(
        latin=DrawingFont(typeface="Aptos"),
        sz=size * 100,
    )

    axis.txPr = RichText(
        p=[
            Paragraph(
                pPr=ParagraphProperties(
                    defRPr=character_properties
                ),
                endParaRPr=character_properties,
            )
        ]
    )


def set_data_label_font_size(chart, size=14):
    """Increase chart data-label font size."""

    character_properties = CharacterProperties(
        latin=DrawingFont(typeface="Aptos"),
        sz=size * 100,
        b=True,
    )

    chart.dataLabels.txPr = RichText(
        p=[
            Paragraph(
                pPr=ParagraphProperties(
                    defRPr=character_properties
                ),
                endParaRPr=character_properties,
            )
        ]
    )


def choose_dollar_axis(max_value):
    """
    Choose readable dollar-axis increments.

    Examples:
        $150 maximum -> $50 increments
        $900 maximum -> $250 increments
        $4,000 maximum -> $1,000 increments
    """

    if max_value <= 0:
        return 50, 200

    target_step = max_value / 4
    magnitude = 10 ** int(log10(target_step))

    for multiplier in (1, 2, 2.5, 5, 10):
        step = multiplier * magnitude

        if step >= target_step:
            break

    maximum = ceil(max_value / step) * step

    return step, maximum


# --------------------------------------------------
# DATABASE QUERIES
# --------------------------------------------------

def get_damage_register():
    """Retrieve all tracked CCD items."""

    with get_connection() as connection:
        rows = connection.execute("""
            SELECT
                job_name,
                description,
                room,
                quantity,
                cost_type,
                current_cost,
                status
            FROM damaged_items
            ORDER BY job_name, description
        """).fetchall()

    return [dict(row) for row in rows]


# --------------------------------------------------
# EXECUTIVE SUMMARY
# --------------------------------------------------

def build_executive_summary(wb, results):
    ws = wb.active
    ws.title = "Executive Summary"

    week_start = results["week_start"].date()
    week_end = (
        results["week_end"] - timedelta(days=1)
    ).date()

    ws.append(["Metric", "Value"])

    metrics = [
        ("Reporting Period", f"{week_start} to {week_end}"),
        ("Previous Week Losses", results["weekly_total"]),
        ("Cumulative Losses", results["cumulative_total"]),
        ("Average Weekly Losses", results["average_weekly_loss"]),
        ("Annualized Previous Week", results["annualized_projection"]),
        ("Annualized Historical", results["annualized_historical"]),
    ]

    for metric, value in metrics:
        if isinstance(value, Decimal):
            value = float(value)

        ws.append([metric, value])

    for row in range(3, ws.max_row + 1):
        ws.cell(row, 2).number_format = CURRENCY_FORMAT

    style_table(ws)

    ws.column_dimensions["A"].width = 42
    ws.column_dimensions["B"].width = 45

    ws.page_setup.fitToHeight = 1


# --------------------------------------------------
# JOB BREAKDOWN
# --------------------------------------------------

def build_job_breakdown(wb, results):
    ws = wb.create_sheet("Job Breakdown")

    ws.append(["Job", "Previous Week Loss"])

    for job, amount in sorted(
        results["weekly_by_job"].items(),
        key=lambda item: item[1],
        reverse=True,
    ):
        ws.append([job, float(amount)])

    for row in range(2, ws.max_row + 1):
        ws.cell(row, 2).number_format = CURRENCY_FORMAT

    style_table(ws)

    ws.column_dimensions["A"].width = 55
    ws.column_dimensions["B"].width = 30


# --------------------------------------------------
# DAMAGE REGISTER
# --------------------------------------------------

def build_damage_register(wb, records):
    ws = wb.create_sheet("Damage Register")

    ws.append([
        "Job",
        "Description",
        "Room",
        "Quantity",
        "Cost Type",
        "Current Cost",
        "Status",
    ])

    for record in records:
        cost = record["current_cost"]

        ws.append([
            record["job_name"],
            record["description"],
            record["room"],
            record["quantity"],
            record["cost_type"],
            float(Decimal(cost)) if cost is not None else None,
            record["status"],
        ])

    for row in range(2, ws.max_row + 1):
        ws.cell(row, 6).number_format = CURRENCY_FORMAT

    style_table(ws)

    column_widths = {
        "A": 24,
        "B": 36,
        "C": 22,
        "D": 14,
        "E": 20,
        "F": 20,
        "G": 18,
    }

    for column, width in column_widths.items():
        ws.column_dimensions[column].width = width


# --------------------------------------------------
# HISTORICAL TRENDS TABLE
# --------------------------------------------------

def build_historical_trends(wb, results):
    ws = wb.create_sheet("Historical Trends")

    ws.append([
        "Week Starting",
        "Weekly Loss",
        "Cumulative Loss",
    ])

    running_total = Decimal("0")

    for week in results["weekly_history"]:
        running_total += week["total"]

        ws.append([
            week["week_start"].strftime("%b %d, %Y"),
            float(week["total"]),
            float(running_total),
        ])

    for row in range(2, ws.max_row + 1):
        ws.cell(row, 2).number_format = CURRENCY_FORMAT
        ws.cell(row, 3).number_format = CURRENCY_FORMAT

    style_table(ws)

    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 30
    ws.column_dimensions["C"].width = 30


# --------------------------------------------------
# CHART WORKSHEET FORMATTING
# --------------------------------------------------

def configure_chart_sheet(ws):
    """Configure a separate printable worksheet for each chart."""

    configure_printing(ws, repeat_headers=False)

    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 1

    ws.sheet_view.showGridLines = False
    ws.print_area = "A1:P35"

    for column_number in range(1, 17):
        column_letter = get_column_letter(column_number)
        ws.column_dimensions[column_letter].width = 10

    for row_number in range(1, 36):
        ws.row_dimensions[row_number].height = 20


def show_no_data_message(ws):
    """Display a message instead of an empty chart."""

    from openpyxl.styles import Font, Alignment

    ws.merge_cells("B10:N13")

    cell = ws["B10"]
    cell.value = (
        "No financial losses recorded "
        "for this reporting period."
    )

    cell.font = Font(
        name="Aptos",
        size=18,
        bold=True,
        color="666666",
    )

    cell.alignment = Alignment(
        horizontal="center",
        vertical="center",
        wrap_text=True,
    )

# --------------------------------------------------
# WEEKLY LOSS CHART
# --------------------------------------------------

def build_weekly_loss_chart(wb):
    data_ws = wb["Historical Trends"]
    ws = wb.create_sheet("Weekly Loss Chart")

        # Don't create a chart when there is no data.
    if data_ws.max_row <= 1:
        configure_chart_sheet(ws)
        show_no_data_message(ws)
        return

    chart = BarChart()
    chart.type = "col"
    chart.style = 10

    chart.title = "Weekly Financial Losses"
    chart.y_axis.title = "Loss ($)"
    chart.x_axis.title = "Reporting Week"

    # Determine readable dollar increments.
    values = [
        float(data_ws.cell(row, 2).value or 0)
        for row in range(2, data_ws.max_row + 1)
    ]

    step, maximum = choose_dollar_axis(
        max(values, default=0)
    )

    chart.y_axis.scaling.min = 0
    chart.y_axis.scaling.max = maximum
    chart.y_axis.majorUnit = step
    chart.y_axis.numFmt = '"$"#,##0'
    chart.y_axis.tickLblPos = "nextTo"

    # Display reporting-week dates.
    chart.x_axis.tickLblPos = "nextTo"

    set_axis_font_size(chart.x_axis, 14)
    set_axis_font_size(chart.y_axis, 14)

    chart.add_data(
        Reference(
            data_ws,
            min_col=2,
            min_row=1,
            max_row=data_ws.max_row,
        ),
        titles_from_data=True,
    )

    if data_ws.max_row > 1:
        chart.set_categories(
            Reference(
                data_ws,
                min_col=1,
                min_row=2,
                max_row=data_ws.max_row,
            )
        )

    # Display exact dollar values above bars.
    chart.dataLabels = DataLabelList()
    chart.dataLabels.showVal = True
    chart.dataLabels.dLblPos = "outEnd"

    set_data_label_font_size(chart, 14)

    # One series, so no legend is necessary.
    chart.legend = None

    chart.width = 25
    chart.height = 16

    ws.add_chart(chart, "B2")
    configure_chart_sheet(ws)


# --------------------------------------------------
# CUMULATIVE LOSS CHART
# --------------------------------------------------

def build_cumulative_loss_chart(wb):
    data_ws = wb["Historical Trends"]
    ws = wb.create_sheet("Cumulative Loss Chart")

        # Don't create a chart when there is no data.
    if data_ws.max_row <= 1:
        configure_chart_sheet(ws)
        show_no_data_message(ws)
        return

    chart = LineChart()
    chart.style = 13

    chart.title = "Cumulative Financial Losses"
    chart.y_axis.title = "Total Loss ($)"
    chart.x_axis.title = "Reporting Week"

    # Determine readable dollar increments.
    values = [
        float(data_ws.cell(row, 3).value or 0)
        for row in range(2, data_ws.max_row + 1)
    ]

    step, maximum = choose_dollar_axis(
        max(values, default=0)
    )

    chart.y_axis.scaling.min = 0
    chart.y_axis.scaling.max = maximum
    chart.y_axis.majorUnit = step
    chart.y_axis.numFmt = '"$"#,##0'
    chart.y_axis.tickLblPos = "nextTo"

    chart.x_axis.tickLblPos = "nextTo"

    set_axis_font_size(chart.x_axis, 14)
    set_axis_font_size(chart.y_axis, 14)

    chart.add_data(
        Reference(
            data_ws,
            min_col=3,
            min_row=1,
            max_row=data_ws.max_row,
        ),
        titles_from_data=True,
    )

    if data_ws.max_row > 1:
        chart.set_categories(
            Reference(
                data_ws,
                min_col=1,
                min_row=2,
                max_row=data_ws.max_row,
            )
        )

    # Visible markers for each week's cumulative total.
    for series in chart.series:
        series.marker.symbol = "circle"
        series.marker.size = 10
        series.graphicalProperties.line.width = 28575

    # Display exact dollar values near points.
    chart.dataLabels = DataLabelList()
    chart.dataLabels.showVal = True
    chart.dataLabels.dLblPos = "t"

    set_data_label_font_size(chart, 14)

    # Position legend beneath the chart.
    if chart.legend is not None:
        chart.legend.position = "b"

    chart.width = 25
    chart.height = 16

    ws.add_chart(chart, "B2")
    configure_chart_sheet(ws)


# --------------------------------------------------
# REPORT GENERATION
# --------------------------------------------------

def generate_report():
    """Generate the complete Excel management report."""

    events = get_financial_events()
    results = calculate_analytics(events)
    damage_records = get_damage_register()

    wb = Workbook()

    build_executive_summary(wb, results)
    build_job_breakdown(wb, results)
    build_damage_register(wb, damage_records)
    build_historical_trends(wb, results)

    build_weekly_loss_chart(wb)
    build_cumulative_loss_chart(wb)

    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(
        LOCAL_TIMEZONE
    ).strftime("%Y-%m-%d_%H%M")

    filename = f"Breakage_Report_{timestamp}.xlsx"
    output_path = REPORT_DIR / filename

    wb.save(output_path)

    print(f"Excel report generated: {output_path}")

    return output_path


if __name__ == "__main__":
    generate_report()
