"""Small, reviewed HomeScout financial-literacy lessons and quiz keys."""

from __future__ import annotations

LESSONS: tuple[dict[str, object], ...] = (
    {
        "slug": "build-a-rental-budget",
        "title": "Build a rental budget",
        "category": "budgeting",
        "minutes": 4,
        "body": (
            "List take-home income, regular costs, obligations, and the full "
            "cost of moving. Review the remaining amount before choosing a "
            "rent target. SmartRent uses your entered figures only."
        ),
        "source_urls": [],
        "quiz": {
            "question": "Which amount should you compare with planned rent?",
            "options": [
                "Gross income alone",
                "Income after your entered regular costs and obligations",
                "Your savings goal only",
            ],
            "correct": 1,
            "explanation": (
                "A budget view includes other regular costs and obligations, not just gross income."
            ),
        },
    },
    {
        "slug": "rental-deposit-records",
        "title": "Keep clear deposit records",
        "category": "deposits",
        "minutes": 3,
        "body": (
            "Before paying, record the amount, recipient, date, and stated "
            "purpose. Keep the written terms and a payment reference. "
            "HomeScout does not decide deposit rights or guarantee recovery."
        ),
        "source_urls": [],
        "quiz": {
            "question": "What is useful to keep with a deposit record?",
            "options": [
                "Only a verbal promise",
                "Amount, date, recipient, purpose, and written terms",
                "A landlord's password",
            ],
            "correct": 1,
            "explanation": "A clear record helps you remember what was agreed and what you paid.",
        },
    },
    {
        "slug": "emergency-buffer",
        "title": "Plan for unexpected costs",
        "category": "planning",
        "minutes": 3,
        "body": (
            "A buffer can help when housing or household costs change. Set a "
            "target that suits your own circumstances; this lesson does not "
            "prescribe a universal amount."
        ),
        "source_urls": [],
        "quiz": {
            "question": "How should a personal buffer target be chosen?",
            "options": [
                "Use a fixed number that fits everyone",
                "Choose a target that reflects your own circumstances",
                "Borrow to match a sample target",
            ],
            "correct": 1,
            "explanation": (
                "A useful target depends on your income, household, obligations, "
                "and other circumstances."
            ),
        },
    },
    {
        "slug": "move-in-costs",
        "title": "Count the costs of moving",
        "category": "moving",
        "minutes": 4,
        "body": (
            "Consider rent, deposit, transport, moving help, utilities, "
            "internet, furniture, essentials, and cleaning. Mark each figure "
            "as from a listing, entered by you, or estimated."
        ),
        "source_urls": [],
        "quiz": {
            "question": "How does SmartRent distinguish a quoted amount from an estimate?",
            "options": [
                "It labels the evidence source for each line",
                "It treats every amount as a bill",
                "It confirms the cost with the provider",
            ],
            "correct": 0,
            "explanation": (
                "Each planner line carries a source label; it is not a payment or "
                "provider confirmation."
            ),
        },
    },
    {
        "slug": "utilities-and-internet",
        "title": "Track utilities and internet",
        "category": "utilities",
        "minutes": 3,
        "body": (
            "Record bills or estimates separately. The utility summary in "
            "SmartRent uses only figures you enter and should not be treated "
            "as a provider quote or guarantee."
        ),
        "source_urls": [],
        "quiz": {
            "question": "What does the SmartRent utility summary represent?",
            "options": [
                "A provider quote",
                "A summary of amounts you entered",
                "A guaranteed future bill",
            ],
            "correct": 1,
            "explanation": (
                "SmartRent summarizes your own entries and does not source or "
                "guarantee utility prices."
            ),
        },
    },
    {
        "slug": "read-a-rental-agreement",
        "title": "Review an agreement carefully",
        "category": "agreements",
        "minutes": 5,
        "body": (
            "Record dates, rent, deposits, stated obligations, and questions "
            "in one place. Ask the other party for unclear points in writing. "
            "The Lease Guardian is an organizer, not legal advice."
        ),
        "source_urls": [],
        "quiz": {
            "question": "What is the Lease Guardian designed to do?",
            "options": [
                "Make a court decision",
                "Organize user-entered dates, obligations, and questions",
                "Approve a lease",
            ],
            "correct": 1,
            "explanation": (
                "It stores your notes and does not interpret or approve legal documents."
            ),
        },
    },
    {
        "slug": "spot-rental-pressure",
        "title": "Pause when a rental request feels pressured",
        "category": "fraud-safety",
        "minutes": 4,
        "body": (
            "Be careful with urgency, requests to pay before you can verify "
            "the property or terms, and requests to share account credentials. "
            "Check details independently and keep written records. Use the "
            "in-app listing report for suspected scams."
        ),
        "source_urls": ["https://www.centralbank.go.ke/fraud-safety/"],
        "quiz": {
            "question": "What is a sensible response to a high-pressure payment request?",
            "options": [
                "Pause and verify the property and terms independently",
                "Share your account credentials",
                "Pay more quickly",
            ],
            "correct": 0,
            "explanation": "Pause, verify independently, and do not share account credentials.",
        },
    },
    {
        "slug": "mpesa-safety",
        "title": "Protect your M-PESA credentials",
        "category": "payments-safety",
        "minutes": 3,
        "body": (
            "Keep your M-PESA PIN private and review transaction information "
            "in your own trusted channel. SmartRent only stores manual notes "
            "and does not connect to M-PESA or confirm a payment."
        ),
        "source_urls": [
            "https://www.safaricom.co.ke/images/Downloads/my-pesaApp.pdf",
            "https://www.safaricom.co.ke/images/Downloads/Buy-goods-guides.pdf",
        ],
        "quiz": {
            "question": "Should you share your M-PESA PIN to prove a rent payment?",
            "options": [
                "Yes, with a property contact",
                "No, keep it private",
                "Only in a group chat",
            ],
            "correct": 1,
            "explanation": "Safaricom advises customers not to share their M-PESA PIN.",
        },
    },
    {
        "slug": "financial-goals",
        "title": "Break a housing goal into steps",
        "category": "planning",
        "minutes": 3,
        "body": (
            "Choose a target and date, then divide the remaining amount across "
            "the time available. Review the plan if your income or costs "
            "change. A virtual tracker does not hold money."
        ),
        "source_urls": [],
        "quiz": {
            "question": "What does the Move-in Savings Vault do?",
            "options": [
                "Hold or transfer funds",
                "Track manually entered goals and contributions",
                "Open a bank account",
            ],
            "correct": 1,
            "explanation": "The vault is a virtual tracker; no money is received, held, or moved.",
        },
    },
    {
        "slug": "needs-and-wants",
        "title": "Separate essentials from optional costs",
        "category": "budgeting",
        "minutes": 3,
        "body": (
            "When planning a move, list essential costs separately from "
            "optional purchases. This makes it easier to adjust timing or "
            "compare choices using your own priorities."
        ),
        "source_urls": [],
        "quiz": {
            "question": "Why separate essentials from optional costs?",
            "options": [
                "To make adjustments and trade-offs clearer",
                "To hide costs",
                "To guarantee a lower rent",
            ],
            "correct": 0,
            "explanation": (
                "Separate lists help you see which costs are flexible for your situation."
            ),
        },
    },
    {
        "slug": "irregular-income-planning",
        "title": "Plan with irregular income",
        "category": "income",
        "minutes": 4,
        "body": (
            "If pay varies, use recent monthly amounts when available and "
            "revisit your estimate. SmartRent shows its default planning "
            "factor when you have not entered recent amounts; the result is "
            "not proof of income or a lending decision."
        ),
        "source_urls": [],
        "quiz": {
            "question": "How can you make an irregular-income estimate more personal?",
            "options": [
                "Enter several recent monthly amounts",
                "Assume every month is the best month",
                "Upload a payslip whether you have one or not",
            ],
            "correct": 0,
            "explanation": "Recent user-entered months replace the default variability factor.",
        },
    },
)


def public_lesson(lesson: dict[str, object]) -> dict[str, object]:
    quiz = lesson["quiz"]
    assert isinstance(quiz, dict)
    return {key: value for key, value in lesson.items() if key != "quiz"} | {
        "quiz": {"question": quiz["question"], "options": quiz["options"]}
    }
