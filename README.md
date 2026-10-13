# CampusBite — Full-stack TypeScript + FastAPI demo

CampusBite is a campus cafeteria ordering prototype for students and faculty. The React frontend is written in TypeScript; the REST API is FastAPI and SQLite persists menu availability and orders.

## Features

- Responsive menu with categories, search, vegetarian filter, prices and availability.
- Cart with quantity controls and server-side price/stock validation.
- Checkout with customer name, campus ID and demo payment-method selection.
- Unique pickup code and order status tracking.
- Cafeteria desk for viewing orders, progressing preparation status, and verifying pickup.
- Staff menu controls to mark dishes available / sold out.
- SQLite database created and seeded automatically on first server start.
- API health endpoint and interactive OpenAPI docs.

## Requirements

- Python 3.10+
- Node.js 20+ and npm

## Start the backend

Open a terminal in `backend/`:

**Windows (PowerShell or Command Prompt)**
```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

**macOS / Linux**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

The API runs at `http://localhost:8000`. Open `http://localhost:8000/docs` to explore endpoints. SQLite data is stored in `backend/campusbite.db`.

## Start the TypeScript frontend

Open a second terminal in `frontend/`:
```bash
npm install
npm run dev
```

Open the Vite URL shown in the terminal, usually `http://localhost:5173`.

The frontend uses `http://localhost:8000/api` by default. To use another API URL, create `frontend/.env` with:
```env
VITE_API_URL=http://localhost:8000/api
```

## Try the demo

1. Start both backend and frontend.
2. Add food to your bag and proceed to checkout.
3. Enter a name and campus ID. Choose a payment method and confirm the order.
4. Keep the generated pickup code and open **Track order** to see its status.
5. Open **Staff desk → Orders**. Move the order from **confirmed** to **preparing**, then **ready**.
6. In **Staff desk → Verify pickup**, enter the code to mark the ready order as collected.
7. Use **Staff desk → Menu & stock** to mark dishes sold out; the menu reflects changes from the API.

## API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/health` | Health and demo-mode status |
| GET | `/api/menu` | Read menu and current stock |
| POST | `/api/orders` | Validate stock and create an order |
| GET | `/api/orders/{pickup_code}` | Look up order status |
| GET | `/api/staff/orders` | List recent orders |
| PATCH | `/api/staff/orders/{order_id}` | Move order through preparation states |
| POST | `/api/staff/verify/{pickup_code}` | Mark a ready order as collected |
| PATCH | `/api/staff/menu/{food_id}` | Update menu availability |

## Important limitations before real campus use

- **Payments are simulated.** Selecting UPI or Card does not charge anyone. Integrate a provider such as Razorpay only after merchant approval, server-side order verification, webhook handling, refunds, and testing. Never trust a client-side “payment successful” flag.
- **Staff endpoints are not authenticated in this demo.** Add proper staff login/roles, secure sessions or tokens, rate limits, audit logs, and authorization before deployment.
- SQLite is fine for a prototype on one server. For production, consider PostgreSQL, backups, migrations, monitoring, HTTPS, and deployment secrets.
- Menu photos use external Unsplash URLs and need internet access. Replace them with approved cafeteria assets for campus launch.
- Confirm cafeteria/Sodexo authorization, menu/pricing accuracy, refund rules, privacy policy, and institutional approval before offering this as a live service.
- The API validates availability and calculates totals on the server. It does not reserve stock or integrate with an actual cafeteria POS yet.

## Project layout

```text
CampusBite-FullStack/
├── backend/
│   ├── main.py
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── tsconfig*.json
│   ├── vite.config.ts
│   └── src/
│       ├── App.tsx
│       ├── main.tsx
│       └── styles.css
└── README.md
```
