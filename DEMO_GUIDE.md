# DB-to-API Generator Demo Guide

This guide walks you through the complete flow of connecting a database, creating queries, and deploying live REST APIs using the `sample.db` provided.

## 🚀 Getting Started

1.  **Launch the App**: Run `run_ui.ps1` and open `http://127.0.0.1:8000`.
2.  **Authenticate**: Copy the `ADMIN_TOKEN` from your terminal, paste it into the top-right "Admin Key" field in the UI, and click **Save**.

---

## 🛠 Step 1: Connect to Database
**Tab**: `Connectors`

Select your database type from the toggle bar and use the following demo inputs:

### Option A: SQLite (Quickest)
| Field | Value |
| :--- | :--- |
| **Internal Name** | `SQLite-Demo` |
| **SQLite File Path** | `sample.db` |
| **Action** | Click **Add Database Connector** |

### Option B: Microsoft SQL Server (MSSQL)
| Field | Value |
| :--- | :--- |
| **Internal Name** | `MSSQL-Server` |
| **Host / Address** | `127.0.0.1` |
| **Port** | `1433` |
| **Database Name** | `SalesDB` |
| **Username** | `sa` |
| **Password** | `YourPassword123` |
| **ODBC Driver** | Select from dropdown (e.g. `ODBC Driver 17 for SQL Server`) |

### Option C: PostgreSQL
| Field | Value |
| :--- | :--- |
| **Internal Name** | `Postgres-Prod` |
| **Host** | `db.example.com` |
| **Database** | `orders_db` |
| **Username** | `postgres` |
| **Password** | `secure_pass` |

### Option D: MySQL
| Field | Value |
| :--- | :--- |
| **Internal Name** | `MySQL-Local` |
| **Host** | `localhost` |
| **Database** | `inventory` |
| **Username** | `root` |
| **Password** | `password` |

---

---

## 🔍 Step 2: Define Queries
**Tab**: `Queries`

### Query A: List All Users
| Activity | Input Value | Expected Output |
| :--- | :--- | :--- |
| **Connector** | Select `MainDB` | |
| **Query Name** | `GetAllUsers` | |
| **SQL Query** | `SELECT * FROM users` | |
| **Action** | Click **Preview** | Data table shows user names, emails, etc. |
| **Action** | Click **Save** | "GetAllUsers" appears in the "Saved Queries" list |

### Query B: User Search (With Parameters)
| Activity | Input Value | Expected Output |
| :--- | :--- | :--- |
| **Query Name** | `GetUserById` | |
| **SQL Query** | `SELECT * FROM users WHERE id = :uid` | "Preview Parameters" box appears with `uid` input |
| **Parameter Value**| Enter `1` in the `uid` box | |
| **Action** | Click **Preview** | Only the user with ID 1 is shown in the results |
| **Action** | Click **Save** | Saved to list |

---

## 🌐 Step 3: Create & Deploy APIs
**Tab**: `API Mappings`

### API 1: Public Users List
| Activity | Input Value | Expected Output |
| :--- | :--- | :--- |
| **Source Query** | `GetAllUsers` | |
| **Method** | `GET` | |
| **Path** | `/api/v1/users` | |
| **Auth Required** | Uncheck | API will be public |
| **Action** | Click **Save & Deployed** | Entry appears in "Live Endpoints" with **GET** |

### API 2: Secure User Detail (Nested Path)
| Activity | Input Value | Expected Output |
| :--- | :--- | :--- |
| **Source Query** | `GetUserById` | |
| **Method** | `GET` | |
| **Path** | `/api/user/:uid` | |
| **Param Builder** | Set `uid` Location to **Path** | |
| **Action** | Click **Save & Deployed** | URL automatically translates to `/api/user/{uid}` |

---

## 🧪 Step 4: Testing the Output
Open a terminal (PowerShell) and run these commands to verify your live APIs.

### 1. Test Public List
**Command:**
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/users" -Method Get
```
**Expected Output:** A JSON array of all users from the database.

### 2. Test Secure Parameterized Path
**Command:**
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/user/1" -Method Get
```
**Expected Output:** JSON object containing details for User ID 1.

---

## 🧹 Step 5: Lifecycle Management
| Feature | Action | Expected Output |
| :--- | :--- | :--- |
| **Undeploy** | Click **Undeploy** on a mapping | The API immediately returns `410 Gone` if hit from terminal. |
| **Delete Mapping**| Click the 🗑️ icon on a mapping | Configuration is removed; route is cleared from memory. |
| **Delete Query** | Click the 🗑️ icon in Queries list | Query is removed. Any mapping using it is auto-disabled. |

---

## 💡 Troubleshooting
*   **401 Unauthorized**: Ensure you defined the mapping as "Public" OR you are passing the admin key in headers for secure endpoints.
*   **Binding Error**: Always ensure your SQL parameter names (e.g., `:id`) exactly match the names in the **Parameter Builder** in the Mappings tab.
