from datetime import datetime

class WebhookManager:
    def __init__(self, app):
        self.app = app
    
    def send_fishing_progress(self):
        if not self.app.webhook_url or not self.app.webhook_enabled:
            return
            
        try:
            import requests
            
            embed = {
                "title": "🎣 GPO Autofish Progress",
                "description": f"Successfully caught **{self.app.webhook_interval}** fish!",
                "color": 0x00ff00,
                "fields": [
                    {"name": "🐟 Total Fish Caught", "value": str(self.app.fish_count), "inline": True},
                    {"name": "⏱️ Session Progress", "value": f"{self.app.webhook_interval} fish in last interval", "inline": True}
                ],
                "footer": {"text": "GPO Autofish - Open Source"},
                "timestamp": datetime.utcnow().isoformat()
            }
            
            payload = {"embeds": [embed], "username": "GPO Autofish Bot"}
            response = requests.post(self.app.webhook_url, json=payload, timeout=10)
            
            if response.status_code == 204:
                print(f"✅ Webhook sent: {self.app.webhook_interval} fish caught!")
            else:
                print(f"❌ Webhook failed: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Webhook error: {e}")
    
    def send_purchase(self, amount):
        if not self.app.webhook_url or not self.app.webhook_enabled:
            return
            
        try:
            import requests
            
            embed = {
                "title": "🛒 GPO Autofish - Auto Purchase",
                "description": f"Successfully purchased **{amount}** bait!",
                "color": 0xffa500,
                "fields": [
                    {"name": "🎣 Bait Purchased", "value": str(amount), "inline": True},
                    {"name": "🐟 Total Fish Caught", "value": str(self.app.fish_count), "inline": True},
                    {"name": "🔄 Status", "value": "Auto purchase completed successfully", "inline": False}
                ],
                "footer": {"text": "GPO Autofish - Auto Purchase System"},
                "timestamp": datetime.utcnow().isoformat()
            }
            
            payload = {"embeds": [embed], "username": "GPO Autofish Bot"}
            response = requests.post(self.app.webhook_url, json=payload, timeout=10)
            
            if response.status_code == 204:
                print(f"✅ Purchase webhook sent: Bought {amount} bait!")
            else:
                print(f"❌ Purchase webhook failed: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Purchase webhook error: {e}")
    
    def send_recovery(self, recovery_info):
        if not self.app.webhook_url or not self.app.webhook_enabled:
            return
            
        try:
            import requests
            
            if recovery_info["recovery_number"] == 1:
                color = 0xffff00
            elif recovery_info["recovery_number"] <= 3:
                color = 0xffa500
            else:
                color = 0xff0000
            
            embed = {
                "title": "🔄 GPO Autofish - Recovery Triggered",
                "description": f"Recovery #{recovery_info['recovery_number']} - System detected stuck state",
                "color": color,
                "fields": [
                    {"name": "🚨 Stuck Action", "value": recovery_info["stuck_state"], "inline": True},
                    {"name": "⏱️ Stuck Duration", "value": f"{recovery_info['stuck_duration']:.1f}s", "inline": True},
                    {"name": "🔢 Recovery Count", "value": str(recovery_info["recovery_number"]), "inline": True},
                    {"name": "🐟 Fish Caught", "value": str(self.app.fish_count), "inline": True},
                    {"name": "📊 Status", "value": "System automatically restarted", "inline": False}
                ],
                "footer": {"text": "GPO Autofish - Recovery"},
                "timestamp": datetime.utcnow().isoformat()
            }
            
            if (self.app.dev_mode or self.app.verbose_logging) and recovery_info.get("state_details"):
                embed["fields"].append({
                    "name": "🔍 Dev Details",
                    "value": str(recovery_info["state_details"])[:1000],
                    "inline": False
                })
            
            payload = {"embeds": [embed], "username": "GPO Autofish Recovery Bot"}
            response = requests.post(self.app.webhook_url, json=payload, timeout=10)
            
            if response.status_code == 204:
                print(f"✅ Recovery webhook sent: Recovery #{recovery_info['recovery_number']}")
            else:
                print(f"❌ Recovery webhook failed: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Recovery webhook error: {e}")
    
    def test(self):
        if not self.app.webhook_url:
            print("❌ Please enter a webhook URL first")
            return
            
        try:
            import requests
            
            embed = {
                "title": "🧪 GPO Autofish Test",
                "description": "Webhook test successful! ✅",
                "color": 0x0099ff,
                "fields": [{"name": "🔧 Status", "value": "Webhook is working correctly", "inline": True}],
                "footer": {"text": "GPO Autofish - Open Source"},
                "timestamp": datetime.utcnow().isoformat()
            }
            
            payload = {"embeds": [embed], "username": "GPO Autofish Bot"}
            response = requests.post(self.app.webhook_url, json=payload, timeout=10)
            
            if response.status_code == 204:
                print("✅ Test webhook sent successfully!")
            else:
                print(f"❌ Test webhook failed: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Test webhook error: {e}")
