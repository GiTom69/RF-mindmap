import google.generativeai as genai
# ... (add your load_api_keys function and setup)

def generate_sub_topics(parent_index, parent_topic, parent_description, ai_model):
    """Asks the AI to brainstorm and format sub-topics."""
    
    prompt = f"""
    You are a subject matter expert creating content for a technical mind map.
    Your task is to break down a parent topic into a detailed list of sub-topics.
    The output must be in a simple CSV format with three columns: Index,Topic,Description.

    Rules:
    1. The parent topic's index is "{parent_index}". All new indices must be children of this (e.g., "{parent_index}.1", "{parent_index}.2").
    2. The topic names should be concise.
    3. The descriptions should be a single, clear sentence explaining the key concept.
    4. Do not include a header row in your output.

    Parent Topic: "{parent_topic}"
    Parent Description: "{parent_description}"

    Generate 5 to 10 relevant sub-topics now.

    Example Output Format:
    {parent_index}.1,First Sub-Topic,This is the explanation for the first sub-topic.
    {parent_index}.2,Second Sub-Topic,This is the explanation for the second sub-topic.
    """
    
    response = ai_model.generate_content(prompt)
    return response.text

# --- How to use it ---
# ai_model = genai.GenerativeModel('models/gemini-flash-latest')
#
# # Example: Expanding the 'Signal Types' topic
# parent_index = "1.1"
# parent_topic = "Signal Types"
# parent_description = "Classification of analog and digital modulation schemes."
#
# new_csv_data = generate_sub_topics(parent_index, parent_topic, parent_description, ai_model)
# print("--- AI Generated CSV Data ---")
# print(new_csv_data)
#
# # You would then review this data and append it to your topics.csv