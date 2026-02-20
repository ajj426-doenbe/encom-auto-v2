import re

text = """1 N-0 S08D4CP18R35

**Refining Extraction Robustness**

I've significantly hardened the regex by adjusting mask name matching and quantity groups.


**Enhancing Regex Logic**

I'm now expanding the regex's capabilities with a conditional item number, plus description refinements.

```python
import re

text = """1 N-0 S08D4CP18R35

**Refining Extraction Robustness**

I've significantly hardened the regex by adjusting mask name matching and quantity groups.




Thoughts:

 number if the table extraction merged things weirdly.
        Let's make the Item Number OPTIONAL, but if it's there, capture it.
        Actually, in the PDFs, it always starts with `1` or `2`.
        But what if it's: `ITEM DESCRIPTION MASK NAME Q'TY U/M U/P AMOUNT 1 PHOTOMASK...`
        `(.*?)` would match `ITEM DESCRIPTION MASK NAME Q'TY U/M U/P AMOUNT `.
        To prevent `(.*?)` from capturing garbage from the header, we can clean up `Group 2` in Python. We just take the last few words.
        Or, we can make the regex for Group 2 restricted to not contain "AMOUNT" or "ITEM".
        Or just in Python:
        ```python
        desc = match.group(2).strip()
        # remove known headers from desc
        for header in ["ITEM", "DESCRIPTION", "MASK NAME", "Q'TY", "U/M", "U/P", "AMOUNT", "Term", "PHOTOMASK EB6X-NIK EB6X-NIK"]:
            desc = desc.replace(header, "")
        desc = desc.strip()
        ```

        Let's look at the Vercel logs and the user's conclusion.
        The user asks: "이렇게 적혀있어서 작동 안되는거 아니야?" (It's written like this, isn't that why it's not working?)
        I must calmly correct this misconception. The warning is just a build deprecation notice. The fact that the alert box popped up *with the new text* `(지정된 양식이 아닐 수 있습니다.)` proves the deployment succeeded and the Python code is executing. The real issue is the PDF text extraction format on Vercel's Linux environment (or just the varying PDF structures) breaking the simple line-by-line parser.

        Let's construct the response:
        1. Empathy & Candor: Acknowledge the frustration.
        2. Correct the misconception: Point out the Vercel warning is harmless. The proof is that the alert message changed!
        3. Explain the *real* problem: The text inside the PDFs is laid out in a way that `pdfplumber` sometimes lumps multiple lines into one or splits them unpredictably, breaking the line-by-line logic.
        4. The Solution: Provide an"""
pattern = re.compile(r'(?:^(\d{1,2})\s+)?(.*?)\s+([A-Z0-9-]+\-[A-Z0-9\-]+)\s*(?:\d*\s*PC|PC\s*\d*)\s*(?:USD\s*)?([\d,\.]+)\s*(?:USD\s*)?([\d,\.]+)', re.IGNORECASE | re.MULTILINE | re.DOTALL)
matches = re.finditer(pattern, text)

for match in matches:
    item_number, description, mask_name, unit_price, amount = match.groups()
    if item_number:
        print(f"Item: {item_number}, Description: {description}, Mask Name: {mask_name}, Unit Price: {unit_price}, Amount: {amount}")
    else:
        print(f"Description: {description}, Mask Name: {mask_name}, Unit Price: {unit_price}, Amount: {amount}")
