Go to the ACM Certificate
Console: https://console.aws.amazon.com/acm/

Click the certificate for lovebhagya.com

You’ll see:

Status: “Pending validation”

Domain status: “Ineligible”

Scroll down to the Domain Validation section.

2. Get the Required DNS Record
You should see something like:

Name (CNAME)	Type	Value
_abc123.lovebhagya.com.	CNAME	_xyz456.acm-validations.aws.

→ Copy both the Name and Value fields exactly.

3. Add the CNAME Record to Route 53
Go to: Route 53 → Hosted Zones → Click on lovebhagya.com

Click “Create record”

Fill in:

Field	Value copied from ACM
Record name	Paste the full CNAME "Name" (even if it starts with _)
Record type	CNAME
Value	Paste the full CNAME "Value"
TTL	300 (default)

⚠️ Be very careful to paste the record exactly, without adding or removing anything.

Click “Create records”

4. Wait for Validation
Wait 5–30 minutes (in rare cases, up to 1–2 hours)

ACM should update the status from:

Ineligible → Pending validation

Then Pending → Issued ✅

✅ Validate It’s Working (Optional)
You can check DNS propagation here:
🔗 https://dnschecker.org
→ Search your CNAME record (_abc123.lovebhagya.com) and make sure it points to the *.acm-validations.aws. value

