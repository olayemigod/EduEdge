# EduEdge User and Institution Profiles

## Goal

Provide a safe self-service profile for Teachers and other EduEdge users, and a permission-aware Institution identity used consistently by the EdgeSuite shell, report cards and communication services.

## Data ownership

### User identity

The standard Frappe `User` remains authoritative for:

- login email;
- first, middle and last name;
- account/profile photo;
- phone and mobile number;
- location and short bio;
- roles and account status.

The profile page never changes login email, roles, password, enabled status, User Type or permission assignments.

### EduEdge User Profile

Sensitive education-facing fields are stored in the one-to-one `EduEdge User Profile`, not as extra fields on `User`:

- preferred display name;
- professional title;
- WhatsApp number;
- preferred communication channel;
- contact address;
- emergency contact name, relationship and phone.

Every non-Administrator user can read and maintain only the profile whose `user` equals the current session user. The target User is server-fixed; the API does not accept an arbitrary User identifier.

### Employee and Instructor

`Employee` remains the official HR record. `Instructor` remains the teaching identity. The profile page displays active links through:

`User → Employee → Instructor`

It does not rewrite Employee, payroll, leave, attendance, designation, department or Instructor ownership.

## Profile navigation and assets

`My Profile` is an account action, not an operational module. It is therefore available from the logged-in user's avatar menu and is not listed as a normal EduEdge sidebar section.

Both the My Profile and Institution Profile Vue applications are compiled through the existing global `eduedge_profile_identity.bundle.js`. Their page loaders mount from that already-loaded runtime and use the same asset as a fallback. Separate `eduedge_my_profile.bundle.js` and `eduedge_institution_profile.bundle.js` entry files were removed to avoid missing lazy-asset mappings after branch changes or partial builds.

## Photo upload safety

User passport/profile photos:

- use standard `User.user_image`;
- may be private files;
- allow JPG, JPEG, PNG and WebP only;
- have a maximum size of 2 MB;
- must be owned by the session user or attached to that exact User.

Institution logos use the same image and size allowlist but must be public so printed reports and approved outbound communication can render them reliably.

## Institution Profile

The Institution Profile page maintains existing `EduEdge Institution` identity plus:

- logo;
- motto;
- phone and WhatsApp number;
- email and website;
- linked Address;
- optional Institution-specific report-card Letter Head;
- report and communication footer.

Institution read and write permissions remain authoritative. Users can select only Institutions returned by the existing Institution access service.

Address editing requires both Institution write permission and normal Address create/write permission. Inline editing is refused when the linked Address is shared with another Institution, Branch or Dynamic Link target.

## Active identity resolution

The shared branding service resolves identity in this order:

1. Institution identity and logo;
2. Company logo only when the Institution has no logo;
3. Branch phone, email and Address as operational overrides;
4. Institution phone, email and Address as fallback.

Branch switching returns the enriched Institution context. The identity bridge clears stale branding and updates the active EdgeSuite tenant logo and contact identity when the selected Branch belongs to another Institution.

## Report cards and communication

Report-card API overrides enrich the existing approved payload with Institution branding. Report rendering uses:

1. Institution-specific Letter Head;
2. otherwise Institution logo, official name, motto and contact profile;
3. otherwise existing Company/Branch fallbacks.

`get_active_communication_identity()` is the reusable internal source for future email, SMS and WhatsApp templates. It exposes only approved Institution/Branch sender identity and does not expose user emergency or home-address information.

## Migration and backward compatibility

- A normal `bench --site <site> migrate` creates `EduEdge User Profile` and adds the new Institution fields.
- Existing Users, Employees, Instructors, Institutions, Branches and report-card records are not rewritten.
- Existing report cards retain Company/Branch fallbacks where Institution branding is incomplete.
- No submitted academic, result, accounting or payroll document is mutated.

## Mandatory QA

### User profile

- Avatar menu contains one `My Profile` action and the EduEdge operational sidebar does not duplicate it.
- Teacher with valid Employee and Instructor links.
- Teacher without Employee/Instructor links.
- Other staff roles.
- Attempt to access another user's profile by list, direct URL and API payload.
- Private photo upload, invalid file type, file over 2 MB and another user's file.
- Name/contact save without altering roles or login email.
- Mobile and tablet layouts.

### Institution profile

- Read-only Teacher versus writable School Administrator.
- One user permitted for one Institution and one permitted for multiple Institutions.
- Cross-Institution API access denial.
- Logo upload/removal and Branch switch between two Institutions.
- Branch contact/address override versus Institution fallback.
- Shared Address refusal.
- Institution-specific Letter Head and no-Letter-Head fallback.
- Report-card logo, name, motto, address, email, phone and footer.

## Latest validation

Head `b3b1a48a685ee3f8428760eef72cb2b9ef801e42` passed EduEdge CI run 2208:

- Python compilation;
- JSON validation;
- all registered frontend entry-script checks;
- 328 pure contract tests.
