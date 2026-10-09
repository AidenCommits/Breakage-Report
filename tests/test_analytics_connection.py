
from analytics import (
    get_financial_events,
    calculate_analytics,
)


def main():
    events = get_financial_events()
    results = calculate_analytics(events)

    print("\nBREAKAGE FINANCIAL ANALYTICS")
    print("-" * 40)

    print(f"Financial events: {len(events)}")

    print(
        f"Current week losses: "
        f"${results['weekly_total']:.2f}"
    )

    print(
        f"Cumulative losses: "
        f"${results['cumulative_total']:.2f}"
    )

    print(
        f"Average weekly losses: "
        f"${results['average_weekly_loss']:.2f}"
    )

    print(
        f"Annualized current week: "
        f"${results['annualized_current_week']:.2f}"
    )

    print(
        f"Annualized historical: "
        f"${results['annualized_historical']:.2f}"
    )

    print("\nLOSSES BY JOB")

    for job, amount in results["weekly_by_job"].items():
        print(f"{job}: ${amount:.2f}")

    print("\nWEEKLY HISTORY")

    for week in results["weekly_history"]:
        print(
            f"{week['week_start'].date()}: "
            f"${week['total']:.2f}"
        )


if __name__ == "__main__":
    main()
