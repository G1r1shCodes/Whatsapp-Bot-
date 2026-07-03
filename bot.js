const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const axios = require('axios');

console.log("Initializing WhatsApp Web Client...");

// Use LocalAuth to save session locally so you don't have to scan QR every time
const client = new Client({
    authStrategy: new LocalAuth(),
    puppeteer: {
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    }
});

// Event: Generate QR Code
client.on('qr', (qr) => {
    console.log("Please scan the QR code below with your WhatsApp:");
    qrcode.generate(qr, { small: true });
});

// Event: Client Ready
client.on('ready', () => {
    console.log('✅ Client is ready! WhatsApp Bot is successfully connected.');
    console.log('Forwarding incoming messages to FastAPI (http://127.0.0.1:8001/whatsapp)...');
});

// === TEST MODE SETTINGS ===
// Set this to true to prevent the bot from replying to real customers
const TEST_MODE = true;
// Add your personal phone number here (with country code and @c.us, e.g., '919876543210@c.us')
const ALLOWED_NUMBERS = ['919205333840', '141957863067780'];
// ==========================

// Event: Incoming Message
client.on('message', async msg => {
    try {
        // Ignore status broadcasts
        if (msg.from === 'status@broadcast') return;

        // Fetch contact details
        const contact = await msg.getContact();
        const profileName = contact.pushname || contact.name || "Unknown";
        // contact.number provides the clean phone number (e.g. "919205333840") instead of the @lid or @c.us format
        const contactNumber = contact.number;
        
        console.log(`\n📥 [${profileName} - ${contactNumber} / ${msg.from}] New Message: ${msg.body}`);

        // Safety Check: If in TEST_MODE, ignore messages from anyone not in ALLOWED_NUMBERS
        if (TEST_MODE && !ALLOWED_NUMBERS.includes(contactNumber)) {
            console.log(`⚠️ [TEST MODE] Ignored message from ${profileName} (${contactNumber}) to prevent accidental replies.`);
            return;
        }

        // Forward message to Python FastAPI backend
        const response = await axios.post('http://127.0.0.1:8001/whatsapp', {
            From: contactNumber,
            Body: msg.body,
            ProfileName: profileName
        });

        // Reply to user on WhatsApp if backend returns a valid reply
        if (response.data && response.data.reply) {
            console.log(`📤 Sending reply to ${profileName}...`);
            await msg.reply(response.data.reply);
        } else {
            console.log("⚠️ Received empty or invalid response from FastAPI backend.");
        }
    } catch (err) {
        console.error("❌ Error processing message or communicating with Python backend:", err.message);
    }
});

// Graceful Shutdown to prevent auth corruption
process.on('SIGINT', async () => {
    console.log('\n🛑 Shutting down WhatsApp client safely...');
    try {
        await client.destroy();
    } catch (e) {}
    process.exit(0);
});

// Start the client
client.initialize();
