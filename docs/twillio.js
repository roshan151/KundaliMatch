<script src="https://media.twiliocdn.com/sdk/js/conversations/v1.4/twilio-conversations.min.js"></script>


<script>
async function initTwilioChat(userId) {
  const res = await fetch('https://lovebhagya.com/twillio:token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ identity: userId })
  });

  const data = await res.json();
  const token = data.token;

  const client = await Twilio.Conversations.Client.create(token);

  client.on('conversationJoined', (conversation) => {
    console.log("Joined:", conversation.friendlyName);
  });

  const conversation = await client.getConversationByUniqueName('chat-room-1');
  const messages = await conversation.getMessages();
  messages.items.forEach(msg => console.log(msg.body));
}
</script>
