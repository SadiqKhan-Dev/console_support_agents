# 🖥️ Console-Based Support Agent System (OpenAI Agents SDK)

A console-based **multi-agent support system** built using the [OpenAI Agents SDK](https://github.com/openai/openai-agents-python).  
This project demonstrates **agent-to-agent handoffs**, **dynamic tool gating with `is_enabled`**, **shared context with Pydantic**, and **guardrails** for safe responses.

---

## 📌 Features

✅ **Triage Agent** that classifies queries (billing, technical, general) and routes them.  
✅ **Specialist Agents**:
- **Billing Agent** → Refunds & invoices  
- **Technical Agent** → Service restarts & status checks  
- **General Support Agent** → FAQs  

✅ **Dynamic Tool Gating**:
- `refund()` enabled **only for premium users**  
- `restart_service()` enabled **only if `issue_type == "technical"`**  

✅ **Context Persistence** using a **Pydantic model** (tracks `name`, `is_premium_user`, `account_id`, `issue_type`).  
✅ **Agent-to-Agent Handoffs** handled automatically.  
✅ **Output Guardrail** prevents apology words like `"sorry"`, `"apologize"`.  
✅ **Streaming Event Display** → Shows handoffs, tool calls, and outputs live in the console.  

---

## 📂 Project Structure

console-support-agents/
│── console_support_agents.py # Main entrypoint
│── .env # API key (not committed)
│── requirements.txt # Dependencies
│── README.md # Documentation




---

## ⚙️ Installation

### 1. Clone the repository
```bash
git clone https://github.com/your-username/console-support-agents.git
cd console-support-agents


2. Create a virtual environment
python -m venv .venv


Activate it:

Windows (PowerShell):

.venv\Scripts\activate


macOS/Linux:

source .venv/bin/activate

3. Install dependencies
pip install -r requirements.txt


Example requirements.txt:

openai-agents>=0.2.11
pydantic>=2.8.2
python-dotenv>=1.0.1

🔑 API Key Setup

Create a file named .env in the project root.

Add your Gemini (OpenAI-compatible) API key:

GEMINI_API_KEY=your_api_key_here


⚠️ If the key is missing, the app will raise:

ValueError: ⚠ GEMINI_API_KEY is missing in .env

🚀 Usage

Run the program:

python console_support_agents.py

Example Console Session
========================================================
 Console Support Agent System  —  OpenAI Agents SDK
 - Triage + Billing + Technical + General
 - Tools w/ dynamic is_enabled
 - Context sharing (Pydantic)
 - Agent-to-agent handoffs
 - Streaming event display
 - Output guardrail (blocks 'sorry'/'apologize')
========================================================
Type 'exit' to quit.

Enter your name (or leave blank): Alice
Are you a premium user? [y/N]: y
Account ID (optional): A123

Context saved: {'name': 'Alice', 'is_premium_user': True, 'issue_type': None, 'account_id': 'A123'}

Ask your question(s). Examples:
 - I want a refund for order 123, amount 49.99
 - Restart the payments service
 - What’s your delivery policy?

You: I want a refund for order 123, amount 49.99

[handoff → Billing Specialist]
[tool call] refund
[tool output] Refund issued for order 123, amount $49.99.

Refund processed successfully for your account.

[context] {'name': 'Alice', 'is_premium_user': True, 'issue_type': 'billing', 'account_id': 'A123'}

🛠️ Agents & Tools
Agent	Tools	Notes
Triage Agent	set_issue_type, update_user_profile	Classifies queries, updates context, performs handoffs.
Billing Agent	refund, invoice_status	refund tool only enabled for premium users.
Technical Agent	restart_service, check_service_status	restart_service only enabled if issue_type == "technical".
General Agent	faq	Handles FAQs and fallback queries.
🧪 Bonus Features

Output Guardrail: Removes outputs containing "sorry", "apologize".

Streaming Events: Every tool call, handoff, and output is printed in real-time.

📖 Example Queries

Billing:
I want a refund for order 456, amount 20.0

Technical:
Restart the payments service

General:
What is your delivery policy?

📜 License

MIT License – feel free to use and modify.

🤝 Contributing

Pull requests are welcome! For major changes, please open an issue first to discuss what you’d like to change.



---

Would you like me to also prepare a **`requirements.txt`** and a **`.env.example`** file so anyone cloning your repo can set it up instantly?
