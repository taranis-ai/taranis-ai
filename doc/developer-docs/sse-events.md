# Server-Side Events Implementation

Server-Side Events (SSE) enable servers to push updates to web clients in real-time. The `SSEManager` class manages these updates, allowing for real-time communication without the need for client-side polling. SSE events are used to push updates from the server to the client over a single HTTP connection.

## Events Defined in `SSEManager.py`

### `news-items-updated`
- **Trigger**: When new news items are added or existing ones are updated.
- **Payload**: Does not send any data; clients are expected to fetch updated news items.

### `report-item-updated`
- **Trigger**: When a specific report item is updated.
- **Payload Details**: Includes data about the updated report item, such as its ID and a summary of changes.
- **Example Payload**: `{ "id": "<report_item_id>", "summary": "Updated content details" }`

### `product-rendered`
- **Trigger**: This event is triggered whenever a product has successfully completed the rendering process within the application.
- **Payload Details**: Includes data about the rendered product, such as its ID and a summary of changes.
- **Example Payload**: `{ "id": "<product_item_id>", "renderDetails": "Details of the rendering process" }`

### `report-item-locked` and `report-item-unlocked`
- **Purpose**: These events play an important role in managing collaborative editing features by signaling the lock and unlock status of report items.
- **Payload Details**:
  - **`report-item-locked`**: Notifies that a report item has been locked for editing, including the item's ID and the identifier of the user who has acquired the lock.
  - **`report-item-unlocked`**: Indicates that a report item has been unlocked, making it available for editing by other users. Includes the item's ID and the identifier of the user releasing the lock.
  - **Example Payload for `report-item-locked`**: `{ "id": "<report_item_id>", "user": "<user_id>" }`


