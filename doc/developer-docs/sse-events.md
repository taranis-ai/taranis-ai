# Server-Side Events Implementation

Server-Side Events (SSE) enable servers to push updates to web clients in real-time. The `SSEManager` class manages these updates, allowing for real-time communication without the need for client-side polling. SSE events are used to push updates from the server to the client over a single HTTP connection.

## Events Defined in `SSEManager.py`

### `news-items-updated`
- **Trigger**: When new news items are added or existing ones are updated.
- **Payload**: Does not send any data; clients are expected to fetch updated news items.

### `report-item-updated`
- **Trigger**: When a specific report item is updated.
- **Payload**: Includes data about the updated report item, such as its ID and a summary of changes.
- **Param data**: `{ "id": "<report_item_id>" }`

### `product-rendered`
- **Trigger**: This event is triggered whenever a product has successfully completed the rendering process within the application.
- **Data Payload**: Includes data about the updated report item, such as its ID and a summary of changes.
- **Param data**: `{ "id": "<product_item_id>" }`

### `report-item-locked` and `report-item-unlocked`
- **Purpose**: Manage collaborative editing by indicating when a report item is locked for editing or unlocked.
- **Payload**: Information about the report item's lock status, including the item ID and the user who has locked the item.



