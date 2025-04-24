def convo_exists():
    db = get_db()
    cursor = db.cursor()
    cursor.execute('''
            SELECT convo_id FROM conversations
            WHERE (user1_id = ? AND user2_id = ?) OR (user1_id = ? AND user2_id = ?)
        ''', (user1_id, user2_id, user2_id, user1_id))
    return cursor.fetchone() is not None

class Mailbox(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    payload = db.Column(db.Text, nullable=False)  # base64 encoded symmetric key for now
    type = db.Column(db.String(50), nullable=False, default="symmetric_key")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@app.route('api/send_symmetric_key', methods=['POST'])
@login_required
def send_symmetric_key(sender_id, recipient_id, payload):
    new_mailbox = Mailbox(
        recipient_id=recipient_id,
        sender_id=sender_id,
        payload=payload,
        type='Symmetric_Key'
    )
    db.session.add(new_mailbox)
    db.session.commit()
    action = direct_message(sender_id, recipient_id)
    return action