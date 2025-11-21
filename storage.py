from typing import Dict, List
from datetime import datetime

class Storage:
    def __init__(self):
        self.user_reports = {}
        self.user_reactions = {}
    
    def add_report(self, user_id: int, report_data: Dict):
        if user_id not in self.user_reports:
            self.user_reports[user_id] = []
        self.user_reports[user_id].append(report_data)
    
    def get_reports(self, user_id: int = None):
        if user_id:
            return self.user_reports.get(user_id, [])
        return self.user_reports
    
    def add_reaction(self, user_id: int, partner_id: int, reaction_type: str):
        if user_id not in self.user_reactions:
            self.user_reactions[user_id] = {}
        self.user_reactions[user_id][partner_id] = reaction_type
    
    def get_reaction(self, user_id: int, partner_id: int):
        return self.user_reactions.get(user_id, {}).get(partner_id)

storage = Storage()