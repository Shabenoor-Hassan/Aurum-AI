"""
Aurum — Smart Investment Guide (AI-Powered Edition)
====================================================
Real AI via Google Gemini API + User Login System
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import os, math, json, datetime
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# ── Secret key for sessions (change this to a random string in production) ────
app.secret_key = os.environ.get("SECRET_KEY", "aurum-secret-key-change-in-production-2024")

# ══════════════════════════════════════════════════════════════════════════════
# GOOGLE GEMINI AI SETUP
# ══════════════════════════════════════════════════════════════════════════════
#
# HOW TO SET UP GEMINI:
# 1. Create an API key from Google AI Studio.
# 2. Create a .env file in the same folder as app.py.
# 3. Add this line to .env:
#      GEMINI_API_KEY=your_real_gemini_key_here
# 4. Install dependencies:
#      pip install -r requirements.txt

try:
    from dotenv import load_dotenv
    from google import genai

    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

    ai_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None
    AI_AVAILABLE = bool(GEMINI_API_KEY and ai_client)
except ImportError:
    GEMINI_API_KEY = ""
    ai_client = None
    AI_AVAILABLE = False
    print("⚠️ google-genai or python-dotenv package not installed. Run: pip install -r requirements.txt")
except Exception as e:
    ai_client = None
    AI_AVAILABLE = False
    print(f"⚠️ Gemini setup failed: {e}")


def ask_ai(system_prompt: str, user_prompt: str, max_tokens: int = 600) -> str:
    """
    Send a prompt to Google Gemini and return response text.
    Falls back to a helpful setup message if AI is unavailable.
    """
    if not AI_AVAILABLE:
        return "⚠️ AI advisor unavailable — please set your GEMINI_API_KEY in the .env file."

    try:
        full_prompt = f"{system_prompt}\n\nUser request:\n{user_prompt}"
        response = ai_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=full_prompt,
        )
        return (response.text or "").strip() or "⚠️ Gemini returned an empty response. Please try again."
    except Exception as e:
        return f"⚠️ AI temporarily unavailable: {str(e)[:100]}"


# ══════════════════════════════════════════════════════════════════════════════
# SIMPLE USER STORE (file-based JSON — replace with a real DB in production)
# ══════════════════════════════════════════════════════════════════════════════

USERS_FILE = "users.json"

def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)

def hash_password(password: str) -> str:
    """Hash passwords securely using Werkzeug's salted password hashing."""
    return generate_password_hash(password)

def verify_password(stored_hash: str, password: str) -> bool:
    """Verify password. Includes legacy SHA-256 support for old demo users."""
    try:
        if stored_hash and stored_hash.startswith(("pbkdf2:", "scrypt:")):
            return check_password_hash(stored_hash, password)
        # Legacy fallback for accounts created before this security fix.
        import hashlib
        return stored_hash == hashlib.sha256(password.encode()).hexdigest()
    except Exception:
        return False

def get_current_user():
    if "user_email" in session:
        users = load_users()
        return users.get(session["user_email"])
    return None


# ══════════════════════════════════════════════════════════════════════════════
# FINANCIAL HELPERS  (same as original)
# ══════════════════════════════════════════════════════════════════════════════

CAGR = {"stocks": 0.124, "mutual": 0.112, "gold": 0.081, "fd": 0.070}

REBAL_TARGETS = {
    "conservative": {"stocks": 0.30, "mutual": 0.30, "gold": 0.20, "fd": 0.20},
    "moderate":     {"stocks": 0.50, "mutual": 0.25, "gold": 0.15, "fd": 0.10},
    "aggressive":   {"stocks": 0.70, "mutual": 0.20, "gold": 0.05, "fd": 0.05},
}

CRASH_IMPACT = {"stocks": 1.00, "mutual": 0.80, "gold": -0.30, "fd": 0.00}

@app.template_filter("commify")
def commify(value):
    try:
        return "{:,}".format(int(value))
    except (ValueError, TypeError):
        return value

def future_value(principal, annual_rate, years):
    return round(principal * (1 + annual_rate) ** years)

def sip_future_value(monthly, annual_rate, months):
    r = annual_rate / 12
    if r == 0:
        return monthly * months
    return round(monthly * ((((1 + r) ** months) - 1) / r) * (1 + r))

def sip_needed(target, annual_rate, years):
    r = annual_rate / 12
    months = years * 12
    if r == 0:
        return target / months
    return round(target / (((((1 + r) ** months) - 1) / r) * (1 + r)))

def years_to_goal(target, monthly, annual_rate):
    r = annual_rate / 12
    if r == 0 or monthly == 0:
        return None
    try:
        n = math.log(1 + (target * r) / (monthly * (1 + r))) / math.log(1 + r)
        return round(n / 12, 1)
    except (ValueError, ZeroDivisionError):
        return None

def calc_health_score(income, expenses, stocks, mutual, gold, fd):
    total = stocks + mutual + gold + fd
    savings = income - expenses
    savings_rate = savings / income if income > 0 else 0
    stock_pct = stocks / total if total > 0 else 0
    assets_used = sum([stocks > 0, mutual > 0, gold > 0, fd > 0])

    sr_score   = min(savings_rate / 0.30, 1) * 25
    exp_score  = min((1 - expenses / income) / 0.50, 1) * 20
    risk_score = (1 if stock_pct <= 0.60 else max(0, 1 - (stock_pct - 0.60) / 0.40)) * 30
    div_score  = (assets_used / 4) * 25

    total_score = round(sr_score + exp_score + risk_score + div_score)
    status = (
        "Excellent" if total_score >= 80 else
        "Good"      if total_score >= 65 else
        "Needs improvement" if total_score >= 50 else
        "Critical"
    )
    breakdown = {
        "savings_rate":    round(sr_score / 25 * 100),
        "expense_ratio":   round(exp_score / 20 * 100),
        "risk_balance":    round(risk_score / 30 * 100),
        "diversification": round(div_score / 25 * 100),
    }
    return total_score, status, breakdown


# ══════════════════════════════════════════════════════════════════════════════
# AUTH ROUTES
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/login", methods=["GET"])
def login_page():
    if get_current_user():
        return redirect("/")
    return render_template("login.html")

@app.route("/api/auth/register", methods=["POST"])
def register():
    data  = request.json
    name  = data.get("name", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not name or not email or not password:
        return jsonify({"error": "All fields are required."}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters."}), 400

    users = load_users()
    if email in users:
        return jsonify({"error": "An account with this email already exists."}), 409

    users[email] = {
        "name":       name,
        "email":      email,
        "password":   hash_password(password),
        "created_at": datetime.datetime.utcnow().isoformat(),
        "profile":    {
            "risk_profile": "moderate",
            "monthly_income": 0,
            "monthly_expenses": 0,
            "investment_goal": "wealth",
        },
        "history": []
    }
    save_users(users)

    session["user_email"] = email
    session.permanent = True
    return jsonify({"success": True, "name": name})

@app.route("/api/auth/login", methods=["POST"])
def login():
    data     = request.json
    email    = data.get("email", "").strip().lower()
    password = data.get("password", "")

    users = load_users()
    user  = users.get(email)

    if not user or not verify_password(user["password"], password):
        return jsonify({"error": "Invalid email or password."}), 401

    # Upgrade old SHA-256 hashes to stronger Werkzeug hashes after a successful login.
    if not user["password"].startswith(("pbkdf2:", "scrypt:")):
        users[email]["password"] = hash_password(password)
        save_users(users)

    session["user_email"] = email
    session.permanent = True
    return jsonify({"success": True, "name": user["name"]})

@app.route("/api/auth/logout", methods=["POST"])
def logout():
    session.pop("user_email", None)
    return jsonify({"success": True})

@app.route("/api/auth/me", methods=["GET"])
def me():
    user = get_current_user()
    if not user:
        return jsonify({"logged_in": False})
    return jsonify({
        "logged_in": True,
        "name":      user["name"],
        "email":     user["email"],
        "profile":   user.get("profile", {}),
    })

@app.route("/api/auth/update-profile", methods=["POST"])
def update_profile():
    user = get_current_user()
    if not user:
        return jsonify({"error": "Not logged in"}), 401
    data = request.json
    users = load_users()
    email = session["user_email"]
    users[email]["profile"].update({
        k: v for k, v in data.items()
        if k in ["risk_profile", "monthly_income", "monthly_expenses", "investment_goal", "experience", "horizon"]
    })
    save_users(users)
    return jsonify({"success": True})


# ══════════════════════════════════════════════════════════════════════════════
# MAIN PAGE
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


# ══════════════════════════════════════════════════════════════════════════════
# AI ADVISOR CHAT  (powered by Gemini)
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/ai-chat", methods=["POST"])
def ai_chat():
    data    = request.json
    message = data.get("message", "").strip()
    history = data.get("history", [])   # list of {role, content}
    user    = get_current_user()

    if not message:
        return jsonify({"error": "No message provided"}), 400

    # Build user context string
    user_ctx = ""
    if user and user.get("profile"):
        p = user["profile"]
        user_ctx = (
            f"\n\nUser profile: Name={user['name']}, "
            f"Risk profile={p.get('risk_profile','moderate')}, "
            f"Monthly income=₹{p.get('monthly_income',0):,}, "
            f"Monthly expenses=₹{p.get('monthly_expenses',0):,}, "
            f"Goal={p.get('investment_goal','wealth')}, "
            f"Experience={p.get('experience','beginner')}, "
            f"Horizon={p.get('horizon','medium')}."
        )

    system = (
        "You are Aurum, an expert Indian investment advisor AI. "
        "You give personalised, specific, actionable advice about Indian financial markets. "
        "You are familiar with SEBI regulations, Indian tax laws (LTCG, STCG, 80C, 80CCD), "
        "and Indian investment instruments: NSE/BSE stocks, mutual funds, ELSS, PPF, NPS, SGBs, "
        "REITs, FDs, RDs, ULIPs, and more. "
        "Be conversational, empathetic, and clear. Use ₹ symbol for amounts. "
        "If you mention specific funds or stocks, always add a disclaimer that it's educational, not advice. "
        "Keep responses concise (3-5 sentences) unless the user asks for detail."
        + user_ctx
    )

    # Build conversation for Gemini
    messages = []
    for h in history[-6:]:  # last 6 turns for context
        messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": message})

    if not AI_AVAILABLE:
        reply = "⚠️ AI advisor is offline. Please configure your GEMINI_API_KEY in the .env file to enable real AI responses."
    else:
        try:
            conversation_text = "\n".join([f"{m['role'].title()}: {m['content']}" for m in messages])
            resp = ai_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=f"{system}\n\nConversation:\n{conversation_text}"
            )
            reply = (resp.text or "").strip() or "Sorry, Gemini returned an empty response. Please try again."
        except Exception as e:
            reply = f"Sorry, I encountered an error: {str(e)[:100]}. Please try again."

    # Save to history if logged in
    if user:
        users = load_users()
        email = session["user_email"]
        if "history" not in users[email]:
            users[email]["history"] = []
        users[email]["history"].append({
            "ts":      datetime.datetime.utcnow().isoformat(),
            "q":       message[:200],
            "a":       reply[:500],
        })
        users[email]["history"] = users[email]["history"][-20:]  # keep last 20
        save_users(users)

    return jsonify({"reply": reply})


# ══════════════════════════════════════════════════════════════════════════════
# GOAL PLANNER
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/goal-planner", methods=["POST"])
def goal_planner():
    data      = request.json
    goal      = data.get("goal", "house")
    target    = float(data.get("target", 5000000))
    monthly   = float(data.get("monthly", 15000))
    years     = int(data.get("years", 10))
    ret_rate  = float(data.get("return_rate", 10)) / 100
    risk_prof = data.get("risk_profile", "moderate")

    projected    = sip_future_value(monthly, ret_rate, years * 12)
    needed       = sip_needed(target, ret_rate, years)
    gap          = round(projected - target)
    on_time      = projected >= target
    actual_years = years_to_goal(target, monthly, ret_rate)
    delay        = round(actual_years - years, 1) if actual_years else None

    curve = []
    for y in range(years + 1):
        val      = sip_future_value(monthly, ret_rate, y * 12)
        invested = monthly * y * 12
        curve.append({"year": y, "value": val, "invested": invested})

    # User context
    user = get_current_user()
    profile_ctx = ""
    if user:
        profile_ctx = f" The user's name is {user['name']}."

    system = (
        "You are Aurum, a certified Indian investment advisor. "
        "Give warm, specific, actionable advice. Use ₹ symbol. Be encouraging but realistic."
        + profile_ctx
    )
    prompt = (
        f"A user wants to achieve: {goal}. "
        f"Target corpus: ₹{target:,.0f}. Time horizon: {years} years. "
        f"Monthly SIP: ₹{monthly:,.0f}. Expected return: {ret_rate*100:.1f}% p.a. "
        f"Risk profile: {risk_prof}. "
        f"Projected corpus: ₹{projected:,.0f}. "
        f"{'They will reach their goal on time — great!' if on_time else f'They will fall short by ₹{abs(gap):,.0f} and be {delay} years late.'} "
        f"Required SIP to meet goal: ₹{needed:,}/month. "
        "Give 3 sentences of specific, actionable advice. "
        "Mention Indian instruments like ELSS, PPF, SGB, or index funds where relevant. "
        "If they are on track, celebrate and suggest how to optimise further. "
        "If they are behind, suggest concrete ways to close the gap."
    )

    ai_advice = ask_ai(system, prompt)

    return jsonify({
        "projected":   projected,
        "needed":      needed,
        "gap":         gap,
        "on_time":     on_time,
        "delay_years": delay,
        "curve":       curve,
        "ai_advice":   ai_advice,
    })


# ══════════════════════════════════════════════════════════════════════════════
# HEALTH SCORE
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/health-score", methods=["POST"])
def health_score():
    data     = request.json
    income   = float(data.get("income", 60000))
    expenses = float(data.get("expenses", 35000))
    stocks   = float(data.get("stocks", 0))
    mutual   = float(data.get("mutual", 0))
    gold     = float(data.get("gold", 0))
    fd       = float(data.get("fd", 0))

    score, status, breakdown = calc_health_score(income, expenses, stocks, mutual, gold, fd)

    system = (
        "You are Aurum, a compassionate Indian financial coach. "
        "Be honest but encouraging. Use plain language, no jargon. "
        "Give practical, India-specific advice."
    )
    prompt = (
        f"Financial health score: {score}/100 ({status}). "
        f"Monthly income: ₹{income:,.0f}, expenses: ₹{expenses:,.0f} "
        f"(savings rate: {round((income-expenses)/income*100 if income > 0 else 0)}%). "
        f"Portfolio: Stocks ₹{stocks:,.0f}, MF ₹{mutual:,.0f}, Gold ₹{gold:,.0f}, FD ₹{fd:,.0f}. "
        f"Score breakdown — Savings: {breakdown['savings_rate']}%, "
        f"Expenses: {breakdown['expense_ratio']}%, "
        f"Risk balance: {breakdown['risk_balance']}%, "
        f"Diversification: {breakdown['diversification']}%. "
        "Give 3 sentences of honest, specific, actionable advice to improve the weakest areas. "
        "Mention specific Indian tools or strategies."
    )

    ai_advice = ask_ai(system, prompt)
    return jsonify({"score": score, "status": status, "breakdown": breakdown, "ai_advice": ai_advice})


# ══════════════════════════════════════════════════════════════════════════════
# PORTFOLIO REBALANCER
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/rebalance", methods=["POST"])
def rebalance():
    data   = request.json
    stocks = float(data.get("stocks", 0))
    mutual = float(data.get("mutual", 0))
    gold   = float(data.get("gold", 0))
    fd     = float(data.get("fd", 0))
    risk   = data.get("risk", "moderate")
    total  = stocks + mutual + gold + fd

    targets = REBAL_TARGETS.get(risk, REBAL_TARGETS["moderate"])
    current = {"stocks": stocks, "mutual": mutual, "gold": gold, "fd": fd}
    changes = {k: round(targets[k] * total - current[k]) for k in current}

    over = [k for k, v in current.items() if total > 0 and v / total > targets[k] + 0.10]

    system = "You are Aurum, a SEBI-compliant Indian portfolio advisor. Be concise and India-specific."
    prompt = (
        f"A {risk}-risk Indian investor needs to rebalance their ₹{total:,.0f} portfolio. "
        f"Currently over-allocated in: {', '.join(over) if over else 'no major area'}. "
        f"Suggested changes: {json.dumps({k: f'₹{v:+,}' for k, v in changes.items()})}. "
        "In 3 sentences: explain why rebalancing now is smart, mention Indian tax implications "
        "(LTCG at 10% on equity gains >₹1L, STCG at 15%), and give one practical tip."
    )

    ai_advice = ask_ai(system, prompt)

    return jsonify({
        "changes":   changes,
        "targets":   {k: round(v * 100, 1) for k, v in targets.items()},
        "current":   {k: round(v / total * 100, 1) if total > 0 else 0 for k, v in current.items()},
        "ai_advice": ai_advice,
    })


# ══════════════════════════════════════════════════════════════════════════════
# CRASH SIMULATOR
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/crash-simulator", methods=["POST"])
def crash_simulator():
    data   = request.json
    stocks = float(data.get("stocks", 0))
    mutual = float(data.get("mutual", 0))
    gold   = float(data.get("gold", 0))
    fd     = float(data.get("fd", 0))
    drop   = float(data.get("drop_pct", 20)) / 100

    total = stocks + mutual + gold + fd
    after = {
        "stocks": round(stocks * (1 - drop * CRASH_IMPACT["stocks"])),
        "mutual": round(mutual * (1 - drop * CRASH_IMPACT["mutual"])),
        "gold":   round(gold   * (1 + drop * abs(CRASH_IMPACT["gold"]))),
        "fd":     round(fd),
    }
    new_total = sum(after.values())
    loss = round(total - new_total)
    gold_pct = gold / total if total > 0 else 0

    system = "You are Aurum, a calm, experienced Indian market veteran. Prevent panic selling with rational advice."
    prompt = (
        f"A {round(drop*100)}% stock market crash scenario for an Indian investor. "
        f"Portfolio before: ₹{total:,.0f}. After simulated crash: ₹{new_total:,.0f}. "
        f"Net loss: ₹{loss:,.0f}. Gold allocation: {round(gold_pct*100)}%. "
        f"Fixed deposits (safe): ₹{fd:,.0f}. "
        "In 3 sentences: advise whether to panic-sell or hold, what specific action to take NOW, "
        "and how to use this crash as an opportunity. Reference real Indian market history (e.g., 2008, 2020 COVID crash recoveries)."
    )

    ai_advice = ask_ai(system, prompt)

    return jsonify({
        "before":   {"stocks": stocks, "mutual": mutual, "gold": gold, "fd": fd, "total": total},
        "after":    {**after, "total": new_total},
        "loss":     loss,
        "loss_pct": round(loss / total * 100, 1) if total > 0 else 0,
        "ai_advice": ai_advice,
    })


# ══════════════════════════════════════════════════════════════════════════════
# SIP CALCULATOR (pure math, no AI needed)
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/sip", methods=["POST"])
def sip_calculator():
    data    = request.json
    monthly = float(data.get("monthly", 5000))
    ret     = float(data.get("annual_return", 12)) / 100
    years   = int(data.get("years", 10))
    step_up = float(data.get("step_up_pct", 10)) / 100

    curve = []
    total_invested = 0
    current_sip    = monthly
    total_value    = 0
    r = ret / 12

    for y in range(1, years + 1):
        for _ in range(12):
            total_value = (total_value + current_sip) * (1 + r)
            total_invested += current_sip
        curve.append({
            "year":     y,
            "value":    round(total_value),
            "invested": round(total_invested),
            "returns":  round(total_value - total_invested),
        })
        current_sip = round(current_sip * (1 + step_up))

    wealth_ratio = round(total_value / total_invested, 2) if total_invested > 0 else 1

    return jsonify({
        "total_invested": round(total_invested),
        "total_value":    round(total_value),
        "total_returns":  round(total_value - total_invested),
        "wealth_ratio":   wealth_ratio,
        "curve":          curve,
    })


# ══════════════════════════════════════════════════════════════════════════════
# AI SUGGESTIONS  (powered by Gemini)
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/suggestions", methods=["POST"])
def suggestions():
    data       = request.json
    experience = data.get("experience", "beginner")
    horizon    = data.get("horizon", "medium")

    # Try to get user profile for personalisation
    user = get_current_user()
    user_ctx = ""
    if user and user.get("profile"):
        p = user["profile"]
        income   = p.get("monthly_income", 0)
        expenses = p.get("monthly_expenses", 0)
        savings  = income - expenses
        if savings > 0:
            user_ctx = f" The user saves approximately ₹{savings:,}/month."

    system = (
        "You are Aurum, an Indian investment advisor. "
        "Return ONLY a valid JSON array — no markdown, no explanation. "
        "Each item must have keys: name, description, risk, return_range, why."
    )
    prompt = (
        f"Suggest 4 investment instruments for an Indian {experience} investor "
        f"with a {horizon}-term horizon.{user_ctx} "
        "For each instrument provide: "
        "name (instrument name), "
        "description (one sentence, max 20 words, practical benefit), "
        "risk (exactly one of: Low / Medium / High), "
        "return_range (e.g. '10–13%'), "
        "why (one sentence explaining why it fits this investor profile). "
        "Include instruments like ELSS, SGBs, index funds, liquid funds, REITs, NPS, PPF as appropriate. "
        "Return ONLY the JSON array, nothing else."
    )

    items = None
    if AI_AVAILABLE:
        try:
            resp = ai_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=f"{system}\n\n{prompt}"
            )
            raw = (resp.text or "").strip().replace("```json", "").replace("```", "").strip()
            items = json.loads(raw)
        except Exception:
            items = None

    if not items:
        # High-quality static fallback
        static = {
            ("beginner", "short"):  [
                {"name": "Liquid Mutual Funds", "description": "Park idle cash, fully liquid, earn 6–7%.", "risk": "Low", "return_range": "6–7%", "why": "Zero lock-in, better than savings account for emergency fund."},
                {"name": "Recurring Deposit", "description": "Fixed monthly savings with guaranteed returns.", "risk": "Low", "return_range": "6.5–7%", "why": "Simple, disciplined savings habit with no market risk."},
                {"name": "Ultra-Short Bond Fund", "description": "Stable debt fund for 3–6 month parking.", "risk": "Low", "return_range": "6.5–7.5%", "why": "Slightly better than FD with high liquidity."},
                {"name": "Short-term FD", "description": "DICGC insured up to ₹5 lakh, guaranteed return.", "risk": "Low", "return_range": "6.5–7.5%", "why": "Safe and predictable for short-term goals."},
            ],
            ("beginner", "medium"): [
                {"name": "Nifty 50 Index Fund", "description": "Own India's 50 biggest companies via SIP.", "risk": "Medium", "return_range": "11–13%", "why": "Lowest cost way to get broad market exposure."},
                {"name": "Balanced Advantage Fund", "description": "Auto-rebalances equity/debt based on market.", "risk": "Medium", "return_range": "9–11%", "why": "Ideal for beginners who fear volatility."},
                {"name": "PPF (Public Provident Fund)", "description": "Government-backed, 7.1% tax-free return.", "risk": "Low", "return_range": "7.1%", "why": "Completely safe, tax-free, builds long-term discipline."},
                {"name": "ELSS (Tax-saving MF)", "description": "Save ₹1.5L tax under 80C, equity growth.", "risk": "Medium", "return_range": "11–14%", "why": "Kills two birds: tax saving + wealth creation."},
            ],
            ("beginner", "long"): [
                {"name": "Nifty 50 SIP", "description": "Systematic monthly investing in top 50 stocks.", "risk": "Medium", "return_range": "12–13%", "why": "Long horizon absorbs volatility, compounding works best here."},
                {"name": "ELSS", "description": "3-year lock-in, equity returns, 80C benefit.", "risk": "Medium", "return_range": "11–14%", "why": "Best tax-saving instrument for long-term investors."},
                {"name": "NPS Tier-1", "description": "Pension fund with additional ₹50k tax deduction.", "risk": "Medium", "return_range": "9–11%", "why": "Extra ₹50k deduction under 80CCD(1B) on top of 80C limit."},
                {"name": "Sovereign Gold Bonds", "description": "2.5% interest + gold appreciation, zero GST.", "risk": "Low", "return_range": "8–12%", "why": "Better than physical gold, tax-free on maturity."},
            ],
            ("intermediate", "medium"): [
                {"name": "Multi-cap Mutual Fund", "description": "Diversified across large, mid, small-cap.", "risk": "Medium", "return_range": "12–15%", "why": "SEBI mandates 25% each in large/mid/small for true diversification."},
                {"name": "Sovereign Gold Bonds (SGB)", "description": "2.5% annual interest + gold price gain.", "risk": "Low", "return_range": "8–12%", "why": "Tax-free on maturity with RBI guarantee — best gold investment."},
                {"name": "REIT", "description": "Commercial real estate income via stock exchange.", "risk": "Medium", "return_range": "8–10%", "why": "Real estate exposure without the hassle of owning property."},
                {"name": "NPS Tier-1 (Aggressive)", "description": "75% equity allocation via NPS for max growth.", "risk": "Medium", "return_range": "9–11%", "why": "Retirement corpus with extra 80CCD(1B) tax benefit."},
            ],
            ("advanced", "long"): [
                {"name": "Momentum Factor Fund", "description": "Nifty 200 Momentum 30 — 5% alpha over Nifty.", "risk": "High", "return_range": "15–18%", "why": "Factor investing has outperformed passive index over long periods."},
                {"name": "International Index Fund", "description": "US/NASDAQ exposure and natural currency hedge.", "risk": "Medium", "return_range": "10–14%", "why": "Reduces India-specific risk, USD appreciation adds returns."},
                {"name": "Direct Equity (Blue Chip)", "description": "Hold 8–10 quality businesses for 10+ years.", "risk": "High", "return_range": "14–18%", "why": "Best returns come from conviction holding, not trading."},
                {"name": "PMS (Portfolio Mgmt Service)", "description": "Actively managed portfolio for ₹50L+ investors.", "risk": "High", "return_range": "15–20%", "why": "Professional management with concentrated, high-conviction bets."},
            ],
        }
        key = (experience, horizon)
        items = static.get(key, static[("beginner", "medium")])

    return jsonify({"suggestions": items})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
