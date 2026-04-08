// 🧪 MANUAL DEBUG TEST - Paste this in your browser console (F12) and run

async function testEmailConnect() {
  console.clear();
  console.log('═══════════════════════════════════════════════');
  console.log('🧪 DIRECT EMAIL CONNECT TEST');
  console.log('═══════════════════════════════════════════════\n');

  const baseUrl = `http://${window.location.hostname}:8000/api/v1`;
  
  const payload = {
    host: 'imap.gmail.com',
    port: 993,
    username: 'test@test.com',
    password: 'testpass',
    folder: 'INBOX',
    use_ssl: true
  };

  console.log('📤 Sending request to:', `${baseUrl}/email/connect`);
  console.log('📋 Payload:', JSON.stringify(payload, null, 2));
  console.log('\n⏳ Waiting for response...\n');

  const startTime = Date.now();

  try {
    console.log('🌐 Fetching...');
    const response = await fetch(`${baseUrl}/email/connect`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    const elapsed = Date.now() - startTime;
    console.log(`📥 Response received after ${elapsed}ms`);
    console.log(`📊 Status: ${response.status} ${response.statusText}`);
    console.log(`📋 Content-Type: ${response.headers.get('content-type')}`);

    const data = await response.json();
    
    console.log('\n═══════════════════════════════════════════════');
    console.log('✅ SUCCESS - Got response:');
    console.log('═══════════════════════════════════════════════');
    console.log(JSON.stringify(data, null, 2));
    
    if (data.status === 'success') {
      console.log(`\n✅ Connection successful! Found ${data.email_count} emails`);
    } else {
      console.log(`\n❌ Connection failed: ${data.error}`);
    }
    
    return data;
  } catch (error) {
    const elapsed = Date.now() - startTime;
    console.log(`\n❌ ERROR after ${elapsed}ms`);
    console.log(`📛 Error name: ${error.name}`);
    console.log(`📛 Error message: ${error.message}`);
    console.log(`📛 Stack: ${error.stack}`);
    
    console.log('\n═══════════════════════════════════════════════');
    console.log('🔍 DEBUGGING INFO:');
    console.log('═══════════════════════════════════════════════');
    console.log(`Backend URL: ${baseUrl}`);
    console.log(`Window origin: ${window.location.origin}`);
    console.log(`Connected to: ${baseUrl}`);
    
    throw error;
  }
}

// Run it
testEmailConnect().catch(err => {
  console.error('\n🚨 Test failed:', err.message);
});
