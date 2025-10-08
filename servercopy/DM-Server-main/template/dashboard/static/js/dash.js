// API Base URL (adjust based on your Flask server)
const API_BASE = 'http://localhost:5000/api';

// Page Navigation
document.querySelectorAll('.nav-link[data-page]').forEach(link => {
    link.addEventListener('click', (e) => {
        e.preventDefault();
        const page = e.currentTarget.dataset.page;
        showPage(page);
        
        // Update active nav
        document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
        e.currentTarget.classList.add('active');
    });
});

function showPage(pageName) {
    document.querySelectorAll('.page').forEach(p => p.style.display = 'none');
    const page = document.getElementById(`${pageName}-page`);
    if (page) {
        page.style.display = 'block';
        
        // Load page-specific data
        if (pageName === 'dashboard') {
            loadDashboard();
        } else if (pageName === 'create-campaign') {
            loadClientGroups();
        } else if (pageName === 'campaigns') {
            loadAllCampaigns();
        } else if (pageName === 'client-groups') {
            loadClientGroupsList();
        }
    }
}

// Load Dashboard Data
async function loadDashboard() {
    try {
        const response = await fetch(`${API_BASE}/campaigns`);
        const data = await response.json();
        
        if (data.success) {
            const tbody = document.getElementById('recentCampaigns');
            const campaigns = data.campaigns.slice(0, 5); // Show only 5 recent
            
            if (campaigns.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">No campaigns yet</td></tr>';
                return;
            }
            
            tbody.innerHTML = campaigns.map(c => `
                <tr>
                    <td>${c.name}</td>
                    <td>Group ${c.client_group_id || 'N/A'}</td>
                    <td>${getChannelBadges(c)}</td>
                    <td><span class="campaign-status status-${c.status}">${c.status}</span></td>
                    <td>
                        <button class="btn btn-sm btn-outline-primary" onclick="viewCampaignStats(${c.id})">
                            <i class="bi bi-eye"></i> View
                        </button>
                    </td>
                </tr>
            `).join('');
        }
    } catch (error) {
        console.error('Error loading dashboard:', error);
    }
}

// Load Client Groups
async function loadClientGroups() {
    try {
        const response = await fetch(`${API_BASE}/client-groups`);
        const data = await response.json();
        
        if (data.success) {
            const select = document.getElementById('clientGroupSelect');
            select.innerHTML = '<option value="">Select a client group</option>';
            
            data.groups.forEach(group => {
                const option = document.createElement('option');
                option.value = group.group_id;
                option.textContent = `${group.group_name} (${group.client_count} clients)`;
                select.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Error loading client groups:', error);
        showToast('Failed to load client groups', 'error');
    }
}

// Client Group Selection Handler
document.getElementById('clientGroupSelect').addEventListener('change', async (e) => {
    const groupId = e.target.value;
    
    if (groupId) {
        try {
            const response = await fetch(`${API_BASE}/clients/${groupId}`);
            const data = await response.json();
            
            if (data.success) {
                document.getElementById('clientCount').textContent = data.count;
                document.getElementById('clientGroupInfo').style.display = 'block';
            }
        } catch (error) {
            console.error('Error loading client info:', error);
        }
    } else {
        document.getElementById('clientGroupInfo').style.display = 'none';
    }
});

// SMS Character Counter
document.getElementById('smsMessage').addEventListener('input', (e) => {
    document.getElementById('smsCharCount').textContent = e.target.value.length;
});

// Audio File Upload Handler
document.getElementById('audioFile').addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (file) {
        const formData = new FormData();
        formData.append('audio', file);
        
        showLoader();
        
        try {
            const response = await fetch(`${API_BASE}/upload-audio`, {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (data.success) {
                document.getElementById('audioFileName').textContent = file.name;
                document.getElementById('audioFileInfo').style.display = 'block';
                document.getElementById('audioFileInfo').dataset.filepath = data.filepath;
                showToast('Audio file uploaded successfully', 'success');
            } else {
                showToast('Failed to upload audio file', 'error');
            }
        } catch (error) {
            console.error('Error uploading file:', error);
            showToast('Error uploading file', 'error');
        } finally {
            hideLoader();
        }
    }
});

// Launch Campaign Function
async function launchCampaign() {
    // Validate required fields
    const campaignName = document.getElementById('campaignName').value;
    const clientGroup = document.getElementById('clientGroupSelect').value;
    
    if (!campaignName || !clientGroup) {
        showToast('Please fill in campaign name and select a client group', 'error');
        return;
    }
    
    // Prepare campaign data
    const campaignData = {
        name: campaignName,
        description: document.getElementById('campaignDescription').value,
        client_group_id: parseInt(clientGroup),
        email_subject: document.getElementById('enableEmail').checked ? document.getElementById('emailSubject').value : null,
        email_body: document.getElementById('enableEmail').checked ? document.getElementById('emailBody').value : null,
        sms_message: document.getElementById('enableSMS').checked ? document.getElementById('smsMessage').value : null,
        voice_file_path: document.getElementById('enableVoice').checked ? 
            (document.getElementById('audioFileInfo').dataset.filepath || null) : null,
        ai_agent_profile: document.getElementById('enableAIAgent').checked ? {
            name: document.getElementById('agentName').value,
            voice: document.getElementById('agentVoice').value,
            personality: document.getElementById('agentPersonality').value,
            script: document.getElementById('agentScript').value
        } : null,
        social_config: {
            facebook: {
                enabled: document.getElementById('enableFacebook').checked,
                content: document.getElementById('facebookContent').value,
                action: 'post'
            },
            twitter: {
                enabled: document.getElementById('enableTwitter').checked,
                content: document.getElementById('twitterContent').value,
                action: 'post'
            },
            instagram: {
                enabled: document.getElementById('enableInstagram').checked,
                content: document.getElementById('instagramContent').value,
                action: 'post'
            }
        }
    };
    
    showLoader();
    
    try {
        // First, create the campaign
        const createResponse = await fetch(`${API_BASE}/campaigns`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(campaignData)
        });
        
        const createData = await createResponse.json();
        
        if (createData.success) {
            // Then launch it
            const launchResponse = await fetch(`${API_BASE}/launch-campaign`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    campaign_id: createData.campaign.id
                })
            });
            
            const launchData = await launchResponse.json();
            
            if (launchData.success) {
                showToast('Campaign launched successfully!', 'success');
                
                // Show results summary
                let summary = `Campaign launched for ${launchData.results.total_clients} clients.\n\n`;
                
                if (launchData.results.actions.email) {
                    summary += `Emails: ${launchData.results.actions.email.success} sent\n`;
                }
                if (launchData.results.actions.sms) {
                    summary += `SMS: ${launchData.results.actions.sms.success} sent\n`;
                }
                if (launchData.results.actions.voice) {
                    summary += `Voice Calls: ${launchData.results.actions.voice.success} made\n`;
                }
                
                alert(summary);
                
                // Reset form
                resetCampaignForm();
                
                // Navigate to campaigns page
                showPage('campaigns');
            } else {
                showToast('Failed to launch campaign: ' + (launchData.error || 'Unknown error'), 'error');
            }
        } else {
            showToast('Failed to create campaign', 'error');
        }
    } catch (error) {
        console.error('Error launching campaign:', error);
        showToast('Error launching campaign', 'error');
    } finally {
        hideLoader();
    }
}

// Load All Campaigns
async function loadAllCampaigns() {
    try {
        const response = await fetch(`${API_BASE}/campaigns`);
        const data = await response.json();
        
        if (data.success) {
            const tbody = document.getElementById('allCampaigns');
            
            if (data.campaigns.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">No campaigns yet</td></tr>';
                return;
            }
            
            tbody.innerHTML = data.campaigns.map(c => `
                <tr>
                    <td>${c.id}</td>
                    <td>${c.name}</td>
                    <td>Group ${c.client_group_id || 'N/A'}</td>
                    <td><span class="campaign-status status-${c.status}">${c.status}</span></td>
                    <td>${new Date(c.created_at).toLocaleDateString()}</td>
                    <td>
                        <button class="btn btn-sm btn-outline-primary" onclick="viewCampaignStats(${c.id})">
                            <i class="bi bi-graph-up"></i> Stats
                        </button>
                    </td>
                </tr>
            `).join('');
        }
    } catch (error) {
        console.error('Error loading campaigns:', error);
    }
}

// View Campaign Stats
async function viewCampaignStats(campaignId) {
    try {
        const response = await fetch(`${API_BASE}/campaign-stats/${campaignId}`);
        const data = await response.json();
        
        if (data.success) {
            const stats = data.stats;
            alert(`Campaign Statistics for: ${stats.name}\n\n` +
                  `Status: ${stats.status}\n` +
                  `Emails Sent: ${stats.email.sent}\n` +
                  `SMS Sent: ${stats.sms.sent}\n` +
                  `Calls Made: ${stats.voice.calls_made}\n` +
                  `Social Posts: ${stats.social.posts}`);
        }
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

// Load Client Groups List
async function loadClientGroupsList() {
    try {
        const response = await fetch(`${API_BASE}/client-groups`);
        const data = await response.json();
        
        if (data.success) {
            const container = document.getElementById('clientGroupsList');
            
            if (data.groups.length === 0) {
                container.innerHTML = '<p class="text-muted">No client groups found</p>';
                return;
            }
            
            container.innerHTML = data.groups.map(group => `
                <div class="p-3 mb-2 border rounded">
                    <h5>${group.group_name}</h5>
                    <p class="mb-0">Group ID: ${group.group_id} | Clients: ${group.client_count}</p>
                </div>
            `).join('');
        }
    } catch (error) {
        console.error('Error loading client groups:', error);
    }
}

// Helper Functions
function getChannelBadges(campaign) {
    const badges = [];
    if (campaign.email_subject) badges.push('<span class="badge bg-primary">Email</span>');
    if (campaign.sms_message) badges.push('<span class="badge bg-success">SMS</span>');
    if (campaign.voice_file_path) badges.push('<span class="badge bg-warning">Voice</span>');
    if (campaign.ai_agent_profile) badges.push('<span class="badge bg-info">AI Agent</span>');
    return badges.join(' ') || '<span class="badge bg-secondary">None</span>';
}

function resetCampaignForm() {
    document.getElementById('campaignName').value = '';
    document.getElementById('campaignDescription').value = '';
    document.getElementById('clientGroupSelect').value = '';
    document.getElementById('emailSubject').value = '';
    document.getElementById('emailBody').value = '';
    document.getElementById('smsMessage').value = '';
    document.getElementById('agentName').value = '';
    document.getElementById('agentPersonality').value = '';
    document.getElementById('agentScript').value = '';
    document.getElementById('facebookContent').value = '';
    document.getElementById('twitterContent').value = '';
    document.getElementById('instagramContent').value = '';
    
    // Uncheck all checkboxes
    document.querySelectorAll('input[type="checkbox"]').forEach(cb => cb.checked = false);
    
    // Hide file info
    document.getElementById('audioFileInfo').style.display = 'none';
    document.getElementById('clientGroupInfo').style.display = 'none';
}

function showLoader() {
    document.getElementById('loader').classList.add('show');
}

function hideLoader() {
    document.getElementById('loader').classList.remove('show');
}

function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type === 'error' ? 'danger' : type === 'success' ? 'success' : 'primary'} border-0`;
    toast.setAttribute('role', 'alert');
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">${message}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;
    
    document.getElementById('toastContainer').appendChild(toast);
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
    
    setTimeout(() => toast.remove(), 5000);
}

// Initialize on load
document.addEventListener('DOMContentLoaded', () => {
    loadDashboard();
    
    // Test database connection
    fetch(`${API_BASE}/test-connection`)
        .then(res => res.json())
        .then(data => {
            if (!data.success) {
                showToast('Database connection failed. Please check your configuration.', 'error');
            }
        });
});