# EduEdge Role and Permission Audit

## Purpose

This audit makes Frappe Role Permission Manager the normal source of truth for EduEdge access while retaining backend enforcement only where business correctness, school-branch isolation, public-exam authority, approved-record integrity, or accounting safety requires it.

The design applies to:

- EduEdge roles;
- Frappe Education roles;
- relevant ERPNext operational roles;
- custom school roles created later;
- EdgeSuite menus, Pages, API actions, reports, lists, and native Frappe forms.

## Access model

EduEdge access has four layers.

1. **Role Permission Manager** grants DocType rights such as Read, Create, Write, Delete, Report, Import, Export, Print, Email, and Share.
2. **EduEdge access manifest** converts effective DocType rights into menu, route, card, and action visibility.
3. **User Branch Access and User Permissions** narrow the records visible to a user when branch enforcement is enabled.
4. **Backend safety rules** protect public examinations, branch isolation, approved records, results, and accounting truth.

A role name by itself should not be an operational permission check. A custom role with the required DocType rights should behave like a standard EduEdge role and remain branch-scoped.

## Page and menu behaviour

All EduEdge Page definitions have an empty `roles` table. This does not make protected data public.

- Page shells are neutral so custom Desk roles are not blocked by a second, stale role whitelist.
- The boot-time `eduedge_access_manifest` determines which EduEdge menu items and routes are shown.
- Resource buttons are shown only when the user has the required Read, Create, or Write right.
- A denied direct EduEdge route shows a controlled access message.
- Native Frappe forms and lists continue to use Frappe DocType permissions and record-level permission hooks.

## Default role families

### Platform managers

- System Manager
- EduEdge Super Administrator
- EduEdge Administrator

These roles receive broad EduEdge/Education management defaults. Public-exam authoring is still controlled separately and is not implied by local System Manager access.

### School managers

- School Administrator
- Academic Administrator
- Education Manager

These roles receive broad management defaults for school academic operations, students, EduEdge records, CBT masters, and staff training.

### Academic operators

- Academics User
- Teacher
- Instructor

These roles receive operational academic rights. Teachers and Instructors can create and edit school CBT questions and templates by default, but cannot approve or retire them unless a permission administrator grants the configured review capability.

### Admission operators

- Registrar
- Admission Officer

These roles receive admissions, applicant, student, guardian, and enrolment defaults without unrelated CBT authoring rights.

### Finance readers

- Bursar
- Accounts User
- Accounts Manager

These roles receive only the EduEdge/Education reads needed for student, enrolment, result, branch, and settings context. Their native ERPNext accounting rights remain controlled by ERPNext.

### Specialist EduEdge roles

- EduEdge Public Exam Administrator
- CBT Invigilator
- Student Safety Officer
- School Operations Manager
- School HR Officer
- Procurement Officer

Each receives only the relevant EduEdge defaults. Specialist roles do not automatically inherit broad academic or accounting access.

### Portal-only roles

- Student
- Guardian
- EduEdge Parent

These are portal identities and do not receive EduEdge Desk administration defaults. `EduEdge Parent` is forced to `desk_access = 0`.

### ERPNext roles with no automatic EduEdge academic grants

- HR User / HR Manager
- Purchase User / Purchase Manager
- Stock User / Stock Manager
- Asset User / Asset Manager
- Sales User / Sales Manager
- Projects User / Projects Manager

These roles keep their native ERPNext permissions. EduEdge does not grant them unrelated academic access simply because ERPNext is installed. A school may deliberately add EduEdge rights through Role Permission Manager.

## Default operational summary

| Role family | Main default access | Important default restriction |
|---|---|---|
| Platform managers | Broad EduEdge and Education management | Public exams still require central authority/capability |
| School managers | Broad school, branch, student, academic, CBT, result, and training management | Cannot bypass branch/public/approved-record safety rules |
| Teacher / Instructor | Academic operations; create/write school CBT Questions and Templates | No CBT approval/retirement by default |
| Academics User | Academic operations and selected read access | No CBT Question authoring by default |
| Registrar / Admission Officer | Admissions, applicants, students, guardians, enrolment | No unrelated CBT authoring |
| CBT Invigilator | Centre, approved Template, Student Group and Assessment Plan visibility | No Question Bank answer access |
| Bursar / Accounts | Necessary student, enrolment, result, branch and settings reads | No academic write by default |
| Student Safety Officer | Student, Guardian, branch and Student Group visibility | No broad academic administration |
| ERPNext HR/Stock/Purchase/Sales/etc. | Native ERPNext rights only | No automatic EduEdge academic access |
| Student / Guardian / Parent | Portal workflows only | No Desk administration |

## Configurable review and oversight capabilities

EduEdge avoids fixed Python role lists for ordinary approval delegation.

### CBT Question review

The configured **Delete** right on `EduEdge CBT Question` is used as the school Question review capability.

- School managers receive it by default.
- Teacher and Instructor do not receive it by default.
- Granting it allows approval and retirement of school Questions.
- Public Question approval still requires ProcessEdge/CoreEdge public-author authority.
- Approved and Retired Questions cannot actually be deleted; the controller preserves audit history.
- A user with Delete may still delete a Draft Question, subject to normal Frappe permissions and branch scope.

### CBT Exam Template review

The configured **Delete** right on `EduEdge CBT Exam Template` is used as the school Template review capability under the same rules.

### Training oversight

The configured **Delete** right on `EduEdge Training Progress` is used as staff-training oversight capability.

- School and platform managers receive it by default.
- Other staff may operate only their own Training Progress records.
- The permission hook uses a non-recursive role-permission resolver.

## Branch governance permissions

Branch Governance no longer depends on named roles.

- View governance: Read on School Branch, User Branch Access, or Instructor Branch Assignment.
- View named assignments: Read on User Branch Access.
- Add or edit assignments: Create or Write on User Branch Access.
- Manage branch/accounting defaults: Write on School Branch.
- Enable or disable branch enforcement: Write on EduEdge Settings.

All-branch governance visibility is granted only when the user has one of these management rights. Other authorised users remain limited to their allowed branches.

## Server-side rules that remain mandatory

School administrators cannot disable these through Role Permission Manager because they protect product truth:

- branch/company isolation when enforcement is enabled;
- centrally owned public-exam records and CoreEdge capability checks;
- approved/retired Question and Template immutability;
- result publication and approval integrity;
- submitted ERPNext accounting-document integrity;
- validation of dependent academic and branch combinations;
- permission-aware create, save, delete, import, and API operations.

These rules narrow an otherwise granted right; they do not replace Role Permission Manager as the normal grant source.

## Migration behaviour

The baseline migration:

1. copies existing standard Frappe/ERPNext permissions into `Custom DocPerm` before adding rows;
2. adds only missing EduEdge defaults;
3. does not revoke existing permissions;
4. runs once through the V0.8 patch and during a fresh installation;
5. does not re-seed defaults on every migration;
6. removes stale EduEdge Page role rows so source and database remain permission neutral.

Later Role Permission Manager changes therefore remain deliberate school configuration.

## Deployment commands

```bash
cd ~/frappe-bench/apps/eduedge
git pull --ff-only origin agent/eduedge-v0-8a-cbt-foundation

cd ~/frappe-bench
bench --site eduedge.local migrate
bench build --app eduedge
bench --site eduedge.local clear-cache
bench --site eduedge.local clear-website-cache
```

## Run the installed-role audit

```bash
bench --site eduedge.local execute eduedge.permissions_baseline.get_role_permission_audit
```

The response reports:

- audited EduEdge/Education DocTypes;
- missing baseline defaults;
- every installed role and its effective audited rights;
- portal-only roles;
- ERPNext roles intentionally receiving no EduEdge defaults;
- active custom/unclassified Desk roles for manual review;
- any stale EduEdge Page role gate still present.

Expected healthy results:

- `missing_defaults` is empty after migration;
- `remaining_page_role_gates` is empty;
- custom roles appear under `unclassified_desk_roles` until deliberately reviewed;
- no unrelated ERPNext role receives unexpected EduEdge rights.

## Manual QA gate

Use separate non-Administrator test users.

### School Administrator

- sees broad EduEdge school-management menus;
- can manage branch access and EduEdge Settings;
- can approve school CBT Questions and Templates;
- cannot author centrally owned public examinations without the required public capability.

### Teacher

- sees academic areas granted to Teacher;
- can create and edit school CBT Questions and Templates;
- cannot approve or retire them by default;
- sees only allowed branches when branch enforcement is active.

### CBT Invigilator

- can read permitted Examination Centres and approved Templates;
- does not receive Question Bank answer access;
- cannot create or approve Questions by default.

### Registrar or Admission Officer

- sees admissions, applicants, student and enrolment operations;
- does not receive unrelated CBT authoring access.

### Bursar or Accounts user

- sees only the configured student/result/branch/settings context;
- cannot edit academic records unless deliberately granted.

### Custom school role

1. Create a Desk role such as `Subject Coordinator`.
2. Grant Read/Create/Write on `EduEdge CBT Question` through Role Permission Manager.
3. Assign the role and an allowed branch to a test user.
4. Confirm the Question Builder/menu appears and only branch-valid records are available.
5. Remove Read/Create/Write and clear cache.
6. Confirm the menu disappears and direct route access shows a controlled denial.

## Administration boundary

EduEdge does not automatically give School Administrator global access to Frappe Role Permission Manager. Global permission administration can affect Accounts, HR, Stock, Purchase, system security, and every installed app.

System Manager or EduEdge Super Administrator should normally maintain the permission matrix. A deployment may deliberately delegate global Role Permission Manager access after accepting that wider responsibility.
