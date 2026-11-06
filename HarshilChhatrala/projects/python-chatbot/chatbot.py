"""
chatbot.py - Natural Language Regex Intent Classifier Routing System.
Processes incoming text prompts to discover operational paths and perform database matching steps.
"""

import re
import random
import pandas as pd
from typing import Tuple, Dict, Any
import helpers

class RuleBasedLaptopChatbot:
    def __init__(self, dataset_path: str):
        """Initializes internal catalog data frame engines."""
        try:
            self.df = pd.read_csv(dataset_path)
        except Exception:
            # Fallback mock dataset initialization to enforce runtime structural stability
            data = {
                'id': [1, 2, 3, 4, 5, 6, 7, 8],
                'brand': ['Dell', 'HP', 'Lenovo', 'ASUS', 'Apple', 'Apple', 'Dell', 'ASUS'],
                'model': ['Inspiron 15', 'Pavilion x360', 'Legion 5', 'ROG Strix', 'MacBook Air M1', 'MacBook Pro M2', 'XPS 13', 'Vivobook 14'],
                'ram_gb': [8, 16, 16, 32, 8, 16, 16, 8],
                'storage_gb': [512, 512, 1024, 1024, 256, 512, 1024, 256],
                'storage_type': ['SSD', 'SSD', 'SSD', 'SSD', 'SSD', 'SSD', 'SSD', 'SSD'],
                'processor': ['Intel i5', 'Intel i7', 'Ryzen 7', 'Ryzen 9', 'Apple M1', 'Apple M2', 'Intel i7', 'Ryzen 5'],
                'price_inr': [54000, 72000, 95000, 145000, 79000, 129000, 115000, 42000],
                'screen_size_inch': [15.6, 14.0, 15.6, 16.0, 13.3, 14.2, 13.4, 14.0],
                'gpu': ['Intel Iris Xe', 'Intel Iris Xe', 'RTX 3060', 'RTX 4070', 'Apple 7-Core', 'Apple 10-Core', 'Intel Iris Xe', 'AMD Radeon'],
                'in_stock': [True, True, True, True, True, True, False, True]
            }
            self.df = pd.DataFrame(data)

        # Pre-compile analytical Regular Expression maps to optimize internal runtime executions
        self.intents = {
            'greeting': re.compile(r'\b(hi|hello|hey|greetings|wassup|good morning|good afternoon)\b', re.IGNORECASE),
            'comparison': re.compile(r'\b(compare|versus|vs)\b', re.IGNORECASE),
            'brand': re.compile(r'\b(dell|hp|lenovo|asus|apple|macbook|acer|msi)\b', re.IGNORECASE),
            'budget': re.compile(r'\b(under|below|less\s+than|cheaper\s+than)\s+(\d+)\b', re.IGNORECASE),
            'ram': re.compile(r'\b(\d+)\s*(gb|gig\s*bytes)?\s*(ram|memory)\b|\b(\d+)\s*gb\b', re.IGNORECASE),
            'processor': re.compile(r'\b(intel|amd|ryzen|i3|i5|i7|i9|r3|r5|r7|r9|m1|m2|m3)\b', re.IGNORECASE),
            'gaming': re.compile(r'\b(gaming|graphics|rtx|fps|games|heavy\s+tasks)\b', re.IGNORECASE),
            'office': re.compile(r'\b(office|business|work|corporate|excel)\b', re.IGNORECASE),
            'student': re.compile(r'\b(student|college|school|university|study|education)\b', re.IGNORECASE),
            'cheapest': re.compile(r'\b(cheapest|lowest\s+price|most\s+affordable|budget\s+option|low\s+cost)\b', re.IGNORECASE),
            'expensive': re.compile(r'\b(expensive|premium|most\s+costly|highest\s+price|elite|top\s+end)\b', re.IGNORECASE),
            'best_value': re.compile(r'\b(best\s+value|value\s+for\s+money|bang\s+for\s+buck|worth\s+it)\b', re.IGNORECASE),
            'surprise': re.compile(r'\b(surprise\s+me|random|anything|pick\s+one)\b', re.IGNORECASE),
            'availability': re.compile(r'\b(in\s+stock|available|ready\s+to\s+buy|instock)\b', re.IGNORECASE)
        }

        self.fun_responses = [
            "🎯 Mission accomplished! Check out what I found for you:",
            "💻 Found some exceptional choices that match your criteria exactly!",
            "🔥 These units deserve your immediate attention:",
            "🚀 Blast off! Check out these fantastic matching options:",
            "😎 I combed through the hardware registry and pulled these winners:"
        ]

        self.dark_humor = [
            "🔍 I searched every dark corner of the hardware database. Even the laptops gave up on this request.",
            "🦄 Those requirements are more mythical than finding an affordable, fully optioned flagship machine.",
            "🛑 The hardware database respectfully declined your configuration request. Try softening parameters!",
            "💨 Poof! Nothing matches. My parsing engine suggests looking for a magical wand instead.",
            "📉 Error 404: Reasonable expectations not found within this budget ceiling."
        ]

    def process_query(self, user_text: str) -> Dict[str, Any]:
        """
        Parses text prompts against regex maps, routes logic, and formats systemic data response payloads.
        """
        cleaned_text = user_text.strip()
        result_df = self.df.copy()
        matched_any_intent = False
        response_notes = ""

        # Step 1: Resolve explicit programmatic global shortcuts
        if self.intents['greeting'].search(cleaned_text):
            return {
                "type": "greeting",
                "text": "👋 Hello there! I am your automated digital hardware consultant. Describe what you need (e.g., 'Dell laptops under 80000' or 'compare MacBook vs XPS') and let's trace your target machine!",
                "data": pd.DataFrame()
            }

        if self.intents['comparison'].search(cleaned_text):
            comp_res = helpers.compare_laptops(self.df, cleaned_text)
            if not comp_res.empty:
                return {
                    "type": "comparison",
                    "text": f"📊 {random.choice(self.fun_responses)} Here is a direct spec comparison:",
                    "data": comp_res
                }
            else:
                return {
                    "type": "empty",
                    "text": random.choice(self.dark_humor),
                    "data": pd.DataFrame()
                }

        # Step 2: Sequential structural parsing filters
        # Brand Target Filtering
        brand_match = self.intents['brand'].findall(cleaned_text)
        if brand_match:
            matched_any_intent = True
            brands = [b[0].lower() for b in brand_match if b[0]]
            # Map structural variances like macbook to apple
            processed_brands = []
            for b in brands:
                if b == 'macbook':
                    processed_brands.append('apple')
                else:
                    processed_brands.append(b)
            
            result_df = result_df[result_df['brand'].str.lower().isin(processed_brands)]

        # Budget Ceiling Constraint Processing
        budget_match = self.intents['budget'].search(cleaned_text)
        if budget_match:
            matched_any_intent = True
            max_budget = float(budget_match.group(2))
            result_df = result_df[result_df['price_inr'] <= max_budget]

        # RAM Requirement Segment Processing
        ram_matches = self.intents['ram'].findall(cleaned_text)
        if ram_matches:
            # Extract numbers accurately from tuples returned by regex findall
            ram_nums = []
            for groups in ram_matches:
                for item in groups:
                    if item.isdigit():
                        ram_nums.append(int(item))
            if ram_nums:
                matched_any_intent = True
                target_ram = ram_nums[0]
                result_df = result_df[result_df['ram_gb'] >= target_ram]

        # Processing CPU Requirements
        proc_match = self.intents['processor'].search(cleaned_text)
        if proc_match:
            matched_any_intent = True
            term = proc_match.group(1).lower()
            result_df = result_df[
                result_df['processor'].str.lower().str.contains(term) | 
                result_df['model'].str.lower().str.contains(term)
            ]

        # Scenario Profiling Engines
        if self.intents['gaming'].search(cleaned_text):
            matched_any_intent = True
            # Gaming machines focus primarily on high ram configurations and dedicated graphics accelerators
            result_df = result_df[
                (result_df['ram_gb'] >= 16) & 
                (result_df['gpu'].str.upper().str.contains('RTX|GTX|AMD|APPLE'))
            ]
            response_notes += " 🎮 Optimizing pipeline layout specifically for maximum frames and gaming compute overhead."

        if self.intents['office'].search(cleaned_text):
            matched_any_intent = True
            # Business setups value memory scaling over raw gpu speed targets
            result_df = result_df[(result_df['ram_gb'] >= 8) & (result_df['price_inr'] <= 110000)]
            response_notes += " 💼 Balancing configurations for reliable business productivity, office processing, and battery scaling profiles."

        if self.intents['student'].search(cleaned_text):
            matched_any_intent = True
            # Academic baselines focus primarily on reliable storage capabilities and low pricing structures
            result_df = result_df[(result_df['price_inr'] <= 70000)]
            response_notes += " 🎓 Filtering configuration metrics for academic budgets and robust day-to-day use cases."

        # Analytical Boundary Triggers
        if self.intents['cheapest'].search(cleaned_text):
            return {
                "type": "recommendation",
                "text": f"💰 {random.choice(self.fun_responses)} Displaying the most affordable choice available in the registry:",
                "data": helpers.cheapest_laptop(self.df)
            }

        if self.intents['expensive'].search(cleaned_text):
            return {
                "type": "recommendation",
                "text": f"💎 {random.choice(self.fun_responses)} Revealing our premium top-of-the-line configuration option:",
                "data": helpers.expensive_laptop(self.df)
            }

        if self.intents['best_value'].search(cleaned_text):
            return {
                "type": "recommendation",
                "text": f"📈 {random.choice(self.fun_responses)} Here is the highest scoring price-to-performance configuration match:",
                "data": helpers.best_value(self.df)
            }

        if self.intents['surprise'].search(cleaned_text):
            return {
                "type": "recommendation",
                "text": f"🎁 {random.choice(self.fun_responses)} Let's see what the catalog randomly selects for you:",
                "data": helpers.surprise_me(self.df)
            }

        if self.intents['availability'].search(cleaned_text):
            matched_any_intent = True
            result_df = result_df[result_df['in_stock'] == True]

        # Step 3: Default fallback execution logic
        if not matched_any_intent:
            # If no clear filter targets were discovered, process the text as a broad text keyword lookup
            keywords = cleaned_text.lower().split()
            valid_keywords = [k for k in keywords if len(k) > 2]
            
            if valid_keywords:
                matched_rows = []
                for idx, row in self.df.iterrows():
                    search_space = f"{row['brand']} {row['model']} {row['processor']} {row['gpu']}".lower()
                    if any(kw in search_space for kw in valid_keywords):
                        matched_rows.append(idx)
                if matched_rows:
                    result_df = self.df.loc[matched_rows]
                else:
                    result_df = pd.DataFrame()
            else:
                # Return standard base default recommendations sorted by quality index ranking
                temp = self.df.copy()
                temp['score'] = temp.apply(helpers.calculate_score, axis=1)
                temp = temp.sort_values(by='score', ascending=False).head(3)
                return {
                    "type": "recommendation",
                    "text": "✨ I'm displaying some of our highest-rated multi-purpose laptop recommendations below:",
                    "data": temp.drop(columns=['score'])
                }

        # Step 4: Format and finalize response package payload
        if result_df.empty:
            return {
                "type": "empty",
                "text": random.choice(self.dark_humor),
                "data": pd.DataFrame()
            }

        # Inject real-time analytical grading calculations before delivering
        result_df_copy = result_df.copy()
        result_df_copy['calculated_score'] = result_df_copy.apply(helpers.calculate_score, axis=1)
        result_df_sorted = result_df_copy.sort_values(by='calculated_score', ascending=False)
        final_clean_df = result_df_sorted.drop(columns=['calculated_score'])

        text_prefix = f"{random.choice(self.fun_responses)}{response_notes}"
        return {
            "type": "recommendation",
            "text": text_prefix,
            "data": final_clean_df
        }