REQUIREMENT_TYPES = ["FUNCTIONAL", "NON_FUNCTIONAL"]
EXTRACTOR_PROMPT_TEMPLATE = """
    You are a specialized requirement extractor of a Software Engineering degree. 
    You are able to recognize functional and non functional features only in tables or when explicitly indicated.   
    You can identify software requirements by looking for words like "class", "system", "program"
"""

HUMAN_PROMPT_TEMPLATE = """
    I need you te extract all the 
    Extract all the software requirements found in this markdown content. Classify them by FUNCTIONAL and NON_FUNCTIONAL.

    You identify a system requirement as if it has a structured definition like
    "the system must...", "the system needs to...", "the program must...", "the class must..."
    If doesn't match that description, ignore it.
    
    For each req in the found requirements
        -Don't change any name or description when a req is found. Leave them in the given language.
        -Use the attribute type to specify your inferation if not explicitly

    If you dont find any software requirement, dont be afraid to respond with an empty list.
    Here is the given markdown content: 
"""