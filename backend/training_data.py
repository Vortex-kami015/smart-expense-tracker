"""Seed examples used to train the auto-categorizer."""

SEED = {
    "Food & Dining": [
        "swiggy order", "zomato dinner", "dominos pizza", "mcdonalds burger", "starbucks coffee",
        "cafe coffee day", "restaurant lunch", "biryani takeaway", "lunch with friends", "chai and samosa",
        "kfc bucket", "bakery cake", "ice cream parlour", "dhaba dinner", "tiffin service", "breakfast at cafe",
        "pizza hut", "subway sandwich", "haldirams snacks", "food court",
    ],
    "Groceries": [
        "bigbasket groceries", "blinkit order", "zepto vegetables", "dmart monthly shopping", "vegetables and fruits",
        "milk and bread", "reliance fresh", "grocery store", "supermarket", "kirana store rice dal",
        "fruits market", "eggs and paneer", "atta oil sugar", "more supermarket",
    ],
    "Transport": [
        "uber ride", "ola cab", "rapido bike taxi", "petrol pump", "fuel for car", "metro card recharge",
        "bus ticket", "auto rickshaw fare", "irctc train ticket", "parking fee", "toll plaza fastag",
        "diesel", "indigo flight ticket", "vehicle service", "cab to airport",
    ],
    "Shopping": [
        "amazon order", "flipkart purchase", "myntra clothes", "nike shoes", "zara shirt", "ajio jeans",
        "mall shopping", "new headphones", "electronics store", "bought a backpack", "lifestyle store",
        "watch purchase", "sunglasses", "meesho order", "croma laptop accessories",
    ],
    "Bills & Utilities": [
        "electricity bill", "water bill", "jio recharge", "airtel postpaid", "broadband internet bill",
        "gas cylinder", "mobile recharge", "dth recharge tata play", "wifi bill", "maintenance charges",
        "piped gas bill", "vi prepaid recharge", "bsnl bill",
    ],
    "Entertainment": [
        "netflix subscription", "spotify premium", "movie tickets pvr", "inox movie", "amazon prime renewal",
        "hotstar subscription", "concert ticket", "gaming steam purchase", "bowling night", "youtube premium",
        "bookmyshow", "theme park entry", "playstation game",
    ],
    "Health": [
        "pharmacy medicines", "apollo pharmacy", "doctor consultation", "hospital bill", "dental checkup",
        "lab test blood", "gym membership", "medplus", "eye checkup glasses", "health insurance premium",
        "physiotherapy session", "vitamins and supplements", "1mg order",
    ],
    "Education": [
        "udemy course", "coursera subscription", "college fees", "tuition fee", "books and stationery",
        "exam registration fee", "coaching classes", "online course", "notebook and pens", "library fine",
        "school fees", "textbook purchase",
    ],
    "Housing": [
        "house rent", "monthly rent", "pg rent", "home loan emi", "furniture ikea", "plumber charges",
        "electrician repair", "home repair", "society charges", "sofa purchase", "paint and renovation",
    ],
    "Travel": [
        "hotel booking", "makemytrip", "airbnb stay", "goibibo hotel", "holiday trip", "oyo room",
        "resort stay", "travel insurance", "visa fee", "airport lounge", "tour package", "booking.com",
    ],
    "Other": [
        "miscellaneous", "gift for friend", "donation", "atm withdrawal", "bank charges", "fine paid",
        "loan to friend", "stamp duty", "courier charges", "unknown payment",
    ],
}

CATEGORIES = list(SEED.keys())

# Keyword rules are checked first: fast, exact, and explainable.
KEYWORDS = {
    "Food & Dining": ["swiggy", "zomato", "restaurant", "cafe", "pizza", "burger", "starbucks", "dominos", "mcdonald", "kfc", "biryani"],
    "Groceries": ["bigbasket", "blinkit", "zepto", "dmart", "grocery", "groceries", "supermarket", "vegetables"],
    "Transport": ["uber", "ola ", "rapido", "petrol", "diesel", "fuel", "metro", "fastag", "toll", "irctc", "parking"],
    "Shopping": ["amazon", "flipkart", "myntra", "ajio", "meesho", "mall"],
    "Bills & Utilities": ["electricity", "water bill", "recharge", "broadband", "wifi", "postpaid", "dth", "gas cylinder"],
    "Entertainment": ["netflix", "spotify", "hotstar", "prime", "pvr", "inox", "bookmyshow", "movie", "youtube premium"],
    "Health": ["pharmacy", "doctor", "hospital", "dental", "medicine", "gym", "apollo", "medplus", "lab test"],
    "Education": ["udemy", "coursera", "tuition", "college", "course", "exam fee", "school fee", "stationery"],
    "Housing": ["rent", "emi", "furniture", "plumber", "electrician", "renovation"],
    "Travel": ["hotel", "makemytrip", "airbnb", "goibibo", "oyo", "resort", "visa", "tour"],
}
