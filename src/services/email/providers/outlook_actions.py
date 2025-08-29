"""Outlook conversation actions for PA_V2"""
import time

def graph_list_message_ids_by_conversation(session, conversation_id: str, top=200):
    """Get all message IDs in a conversation"""
    url = f"/me/messages?$select=id&$top={top}&$orderby=receivedDateTime desc&$filter=conversationId eq '{conversation_id}'"
    ids = []
    while url:
        r = session.get(url)
        r.raise_for_status()
        data = r.json()
        ids.extend([it["id"] for it in data.get("value", [])])
        url = data.get("@odata.nextLink")
    return ids

def graph_move_message_to_deleted(session, msg_id: str):
    """Move a single message to deleted items"""
    r = session.post(f"/me/messages/{msg_id}/move", json={"destinationId": "deletedItems"})
    r.raise_for_status()

def outlook_soft_delete_conversation(session, conversation_id: str, batch_size=20, delay_s=0.2):
    """Move all messages in a conversation to deleted items"""
    ids = graph_list_message_ids_by_conversation(session, conversation_id)
    for i in range(0, len(ids), batch_size):
        for mid in ids[i:i+batch_size]:
            graph_move_message_to_deleted(session, mid)
        time.sleep(delay_s)

def outlook_restore_from_deleted(session, conversation_id: str, dest_folder="inbox"):
    """Restore messages from deleted items to inbox"""
    ids = graph_list_message_ids_by_conversation(session, conversation_id)
    for mid in ids:
        session.post(f"/me/messages/{mid}/move", json={"destinationId": dest_folder}).raise_for_status()
