# structured-chat-response

## Problem
Currently, the chat replies with text only. When a user asks for a list of documents or contracts, the agent summarizes the data in text format. This makes it difficult for users to visualize, sort, or reuse the data (e.g., copying a list of CNPJs or values).

## Solution
Modify the backend `database_query` tool to capture the raw structured results of the SQL query and pass them through to the API response. The frontend (which already has table rendering logic) will then display this structured data below the chat message.

## How It Works (Technical Flow)
1. **User asks question**: "List all contracts over R$ 10k"
2. **Agent generates SQL**: `SELECT client_name, value FROM contracts WHERE value > 10000`
3. **Tool executes SQL**:
   - Gets raw rows: `[{"client_name": "Acme", "value": 15000}, ...]`
   - **NEW**: Saves this raw data to a "side-channel" (a temporary list in the request context).
   - Returns text summary to Agent: "Found 5 contracts..."
4. **Agent responds**: "I found 5 contracts matching your criteria." (Text only)
5. **API Response**: Combines the Agent's text answer + the side-channel raw data.
6. **Frontend**: Receives JSON `{ "answer": "I found...", "data": [...] }`.
   - Displays text bubble.
   - **Automatically renders a table** below the text using the `data` array.
   - **Displays an "Export" button** (CSV/JSON) above or below the table for easy data extraction.

## Impact
- **Users**: Can view query results in a clear table format and **export them** for use in Excel/Sheets.
- **Dev**: Unlocks future possibilities like exporting data or generating charts.

## Risks
- **Performance**: Returning large datasets might bloat the response. We should respect the existing limit (current limit is 20 rows in text, but maybe we can allow slightly more in JSON, or keep it consistent).
- **Token Usage**: No impact, as the raw data isn't fed back to the LLM (only the summary/text representation is).
