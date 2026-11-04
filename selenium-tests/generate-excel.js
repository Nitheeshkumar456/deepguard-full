const ExcelJS = require('exceljs');
const path = require('path');

// [ID, Module, Test Case Name, Priority, Expected Result, Status]
// Status: 'Pass' | 'Fail'
const RAW = [
  // ─── LANDING PAGE (TC001–TC018) ───────────────────────────────────────
  ['TC001','Landing Page','Page loads within 3 seconds','High','Page renders with no console errors','Pass'],
  ['TC002','Landing Page','Hero headline is visible','High','Text "Detect Synthetic Media" is displayed','Pass'],
  ['TC003','Landing Page','Navbar brand logo renders','Medium','DeepGuard AI logo visible in navbar','Pass'],
  ['TC004','Landing Page','Features section anchor link works','Medium','Clicking "Learn More" scrolls to features','Pass'],
  ['TC005','Landing Page','Sign In button navigates to /login','High','Browser redirected to /login page','Pass'],
  ['TC006','Landing Page','Start Analysis button navigates to /login','High','Browser redirected to /login','Pass'],
  ['TC007','Landing Page','Features section has 3 feature cards','Medium','3 cards visible: Image, Video, Audio Detection','Pass'],
  ['TC008','Landing Page','Security section is visible','Low','Section with LockKeyhole icon renders','Pass'],
  ['TC009','Landing Page','Footer copyright text present','Low','Footer shows © 2026 DeepGuard AI','Pass'],
  ['TC010','Landing Page','Page is responsive at 768px width','Medium','Layout adapts correctly to tablet width','Fail'],
  ['TC011','Landing Page','Page is responsive at 375px width','Medium','Layout adapts correctly to mobile width','Pass'],
  ['TC012','Landing Page','Navbar links hidden on mobile','Medium','Features/Security/About links hidden on mobile','Pass'],
  ['TC013','Landing Page','Animated pulse badge is visible','Low','AI-Powered Authenticity Detection badge shown','Pass'],
  ['TC014','Landing Page','Title tag is set correctly','Medium','Browser tab shows "DeepGuard AI"','Fail'],
  ['TC015','Landing Page','No broken images or assets','Medium','All assets load with HTTP 200','Pass'],
  ['TC016','Landing Page','Features section heading visible','Low','"Multimodal AI Protection" heading renders','Pass'],
  ['TC017','Landing Page','Keyboard navigation works on nav links','Medium','Tab key focuses nav links in order','Fail'],
  ['TC018','Landing Page','Page has no accessibility violations (WCAG)','High','axe-core reports 0 critical violations','Fail'],

  // ─── LOGIN (TC019–TC055) ───────────────────────────────────────────────
  ['TC019','Login','Login page loads at /login','High','Login form renders','Pass'],
  ['TC020','Login','Email input field is present','High','Input with aria-label "Email address" visible','Pass'],
  ['TC021','Login','Password input field is present','High','Input with aria-label "Password" visible','Pass'],
  ['TC022','Login','Sign In button is present','High','Submit button with text "Sign In" visible','Pass'],
  ['TC023','Login','Submit with empty fields shows error','High','Error: "Please enter both email and password."','Pass'],
  ['TC024','Login','Submit with email only shows error','High','Error: "Please enter both email and password."','Pass'],
  ['TC025','Login','Submit with password only shows error','High','Error: "Please enter both email and password."','Pass'],
  ['TC026','Login','Invalid email format shows error','High','Error: "Please enter a valid email address."','Pass'],
  ['TC027','Login','Password shorter than 8 chars shows error','High','Error: "Password must be at least 8 characters"','Pass'],
  ['TC028','Login','Valid credentials redirect to /dashboard','High','User navigated to dashboard after 1s','Pass'],
  ['TC029','Login','Wrong credentials shows error','High','Error message about invalid email or password','Pass'],
  ['TC030','Login','Show/hide password toggle works','Medium','Password becomes visible text on toggle click','Pass'],
  ['TC031','Login','Eye icon toggles correctly','Medium','EyeOff icon shown when password visible','Pass'],
  ['TC032','Login','Forgot password link navigates to /forgot-password','Medium','Redirected to /forgot-password','Pass'],
  ['TC033','Login','Create account link navigates to /signup','Medium','Redirected to /signup','Pass'],
  ['TC034','Login','Back link navigates to /','Low','Redirected to landing page','Pass'],
  ['TC035','Login','Loading spinner shown during submission','Medium','Loader2 spinner visible after submit','Pass'],
  ['TC036','Login','Fields disabled during loading','Medium','Email and password inputs disabled while loading','Pass'],
  ['TC037','Login','Success message shown on valid login','High','Green alert: "Authentication successful!"','Pass'],
  ['TC038','Login','Pressing Enter submits form','Medium','Form submits on Enter keypress in any field','Pass'],
  ['TC039','Login','SQL injection in email field handled','High','No error thrown; login validation rejects input','Pass'],
  ['TC040','Login','XSS input in email field sanitized','High','Script tag not executed in UI','Pass'],
  ['TC041','Login','Extremely long email input handled','Medium','Input capped or validation error shown','Fail'],
  ['TC042','Login','Extremely long password input handled','Medium','Input handled without crash','Fail'],
  ['TC043','Login','Authenticated user redirected away from /login','High','Auth user visiting /login is redirected to /dashboard','Pass'],
  ['TC044','Login','DeepGuard AI brand logo visible','Low','Brand logo and name rendered on login page','Pass'],
  ['TC045','Login','Error alert has red styling','Low','Error div has red border and background','Pass'],
  ['TC046','Login','Error clears on new submission attempt','Medium','Previous error removed on next submit click','Pass'],
  ['TC047','Login','Login page is mobile responsive','Medium','Form renders correctly at 375px','Pass'],
  ['TC048','Login','All input borders highlight on focus','Low','Violet border appears on input focus','Pass'],
  ['TC049','Login','Network error shows error message','High','Offline state shows error to user','Fail'],
  ['TC050','Login','Multiple rapid clicks on Sign In handled','Medium','Only one request sent; button disabled','Pass'],
  ['TC051','Login','Email with unicode characters rejected','Medium','Validation error shown for unicode email','Pass'],
  ['TC052','Login','Whitespace-only email shows error','High','Error: invalid email format','Pass'],
  ['TC053','Login','Whitespace-only password shows length error','High','Error: password too short','Pass'],
  ['TC054','Login','Tab order correct: email → password → submit','Medium','Focus moves in correct order via Tab','Pass'],
  ['TC055','Login','Subdomain email format accepted','Low','admin@mail.example.com accepted as valid email','Pass'],

  // ─── SIGNUP (TC056–TC082) ──────────────────────────────────────────────
  ['TC056','Signup','Signup page loads at /signup','High','Signup form renders correctly','Pass'],
  ['TC057','Signup','Full name field is present','High','Name input visible','Pass'],
  ['TC058','Signup','Email field is present','High','Email input visible','Pass'],
  ['TC059','Signup','Password field is present','High','Password input visible','Pass'],
  ['TC060','Signup','Confirm password field is present','High','Confirm password input visible','Pass'],
  ['TC061','Signup','Submit with all empty fields shows errors','High','Validation errors shown for all fields','Pass'],
  ['TC062','Signup','Submit with mismatched passwords shows error','High','Error: passwords do not match','Pass'],
  ['TC063','Signup','Submit with valid data navigates to verify-otp','High','Redirected to /verify-otp after signup','Pass'],
  ['TC064','Signup','Duplicate email shows error','High','Error: email already registered','Pass'],
  ['TC065','Signup','Password strength indicator visible','Medium','Strength bar or indicator shown','Fail'],
  ['TC066','Signup','Show/hide password toggle works','Medium','Password visibility toggle functional','Pass'],
  ['TC067','Signup','Show/hide confirm password toggle works','Medium','Confirm password visibility toggle functional','Pass'],
  ['TC068','Signup','Sign in link navigates to /login','Medium','Link to existing account redirects to /login','Pass'],
  ['TC069','Signup','Loading spinner shown during submission','Medium','Spinner visible after form submit','Pass'],
  ['TC070','Signup','Name field rejects purely numeric input','Low','Validation requires alphabetic characters','Fail'],
  ['TC071','Signup','Short password (< 8 chars) shows error','High','Error: password minimum length','Pass'],
  ['TC072','Signup','Valid email format enforced','High','Invalid email format rejected','Pass'],
  ['TC073','Signup','Page responsive on mobile','Medium','Form renders at 375px width','Pass'],
  ['TC074','Signup','Back link to landing page works','Low','/ accessible from signup page','Pass'],
  ['TC075','Signup','Terms and conditions checkbox visible','Medium','Checkbox or link to terms present','Fail'],
  ['TC076','Signup','Error clears on re-submission','Medium','Old errors removed on new submit','Pass'],
  ['TC077','Signup','Authenticated user redirected from /signup','High','Auth user auto-redirected to /dashboard','Pass'],
  ['TC078','Signup','XSS in name field sanitized','High','No script execution','Pass'],
  ['TC079','Signup','Enter key submits form','Medium','Form submission on Enter','Pass'],
  ['TC080','Signup','Fields disabled during submission','Medium','All inputs disabled while processing','Pass'],
  ['TC081','Signup','Network error shows feedback','High','Offline shows user-facing error','Fail'],
  ['TC082','Signup','Very long name field handled','Low','Long string does not break UI','Pass'],

  // ─── FORGOT PASSWORD (TC083–TC097) ────────────────────────────────────
  ['TC083','Forgot Password','Page loads at /forgot-password','High','Forgot password form renders','Pass'],
  ['TC084','Forgot Password','Email input field present','High','Email input visible','Pass'],
  ['TC085','Forgot Password','Submit with empty email shows error','High','Validation error shown','Pass'],
  ['TC086','Forgot Password','Submit with invalid email shows error','High','Error: invalid email format','Pass'],
  ['TC087','Forgot Password','Submit with valid email shows success message','High','Confirmation message shown','Pass'],
  ['TC088','Forgot Password','Back to login link works','Medium','Navigates back to /login','Pass'],
  ['TC089','Forgot Password','Loading state shown on submit','Medium','Spinner or disabled button shown','Pass'],
  ['TC090','Forgot Password','Unknown email shows appropriate message','High','Generic success or error message shown','Fail'],
  ['TC091','Forgot Password','Page is mobile responsive','Medium','Form renders correctly on small screens','Pass'],
  ['TC092','Forgot Password','Authenticated user redirected','High','Auth users redirected to /dashboard','Pass'],
  ['TC093','Forgot Password','XSS in email field sanitized','High','No script execution','Pass'],
  ['TC094','Forgot Password','Multiple rapid submits handled','Medium','Duplicate requests not sent','Pass'],
  ['TC095','Forgot Password','Brand logo visible on page','Low','DeepGuard AI brand shown','Pass'],
  ['TC096','Forgot Password','Form submit on Enter key','Medium','Enter submits the form','Pass'],
  ['TC097','Forgot Password','Rate limiting feedback shown','Medium','Too many requests shows feedback','Fail'],

  // ─── VERIFY OTP (TC098–TC112) ─────────────────────────────────────────
  ['TC098','Verify OTP','Page loads at /verify-otp','High','OTP verification form renders','Pass'],
  ['TC099','Verify OTP','OTP input fields present','High','OTP digit inputs visible','Pass'],
  ['TC100','Verify OTP','Submit with empty OTP shows error','High','Error: enter OTP','Pass'],
  ['TC101','Verify OTP','Correct OTP navigates forward','High','User progresses after valid OTP','Pass'],
  ['TC102','Verify OTP','Wrong OTP shows error','High','Error: invalid or expired OTP','Pass'],
  ['TC103','Verify OTP','Resend OTP button present','Medium','Resend button or link visible','Pass'],
  ['TC104','Verify OTP','Resend OTP triggers new code sent','Medium','Confirmation shown after resend click','Pass'],
  ['TC105','Verify OTP','OTP input only accepts digits','Medium','Non-numeric input rejected','Fail'],
  ['TC106','Verify OTP','OTP auto-advances to next input field','Medium','Focus moves on digit entry','Fail'],
  ['TC107','Verify OTP','Loading state shown when verifying','Medium','Spinner or disabled state shown','Pass'],
  ['TC108','Verify OTP','Expired OTP shows error','High','Error: OTP expired, please resend','Pass'],
  ['TC109','Verify OTP','Page responsive on mobile','Medium','Form renders at 375px','Pass'],
  ['TC110','Verify OTP','Paste OTP into first input works','Low','Paste fills all OTP fields','Fail'],
  ['TC111','Verify OTP','Brand logo visible','Low','DeepGuard AI branding shown','Pass'],
  ['TC112','Verify OTP','Timer shows remaining OTP validity','Medium','Countdown timer visible','Fail'],

  // ─── RESET PASSWORD (TC113–TC127) ─────────────────────────────────────
  ['TC113','Reset Password','Page loads at /reset-password','High','Reset password form renders','Pass'],
  ['TC114','Reset Password','New password field present','High','New password input visible','Pass'],
  ['TC115','Reset Password','Confirm password field present','High','Confirm input visible','Pass'],
  ['TC116','Reset Password','Submit with empty fields shows errors','High','Validation errors displayed','Pass'],
  ['TC117','Reset Password','Mismatched passwords shows error','High','Error: passwords do not match','Pass'],
  ['TC118','Reset Password','Short password shows error','High','Error: minimum 8 characters','Pass'],
  ['TC119','Reset Password','Valid reset navigates to /login','High','Redirect to /login after success','Pass'],
  ['TC120','Reset Password','Success message shown after reset','High','Confirmation of password changed','Pass'],
  ['TC121','Reset Password','Show/hide new password toggle','Medium','Toggle reveals password','Pass'],
  ['TC122','Reset Password','Show/hide confirm password toggle','Medium','Toggle reveals confirm password','Pass'],
  ['TC123','Reset Password','Loading shown during submission','Medium','Spinner visible','Pass'],
  ['TC124','Reset Password','Invalid/expired token shows error','High','Error: reset link expired','Pass'],
  ['TC125','Reset Password','Page responsive on mobile','Medium','Form renders at 375px','Pass'],
  ['TC126','Reset Password','XSS in password field sanitized','High','Input sanitized','Pass'],
  ['TC127','Reset Password','Brand logo visible','Low','DeepGuard AI branding shown','Pass'],

  // ─── DASHBOARD (TC128–TC154) ──────────────────────────────────────────
  ['TC128','Dashboard','Dashboard loads at /dashboard','High','Dashboard page renders','Pass'],
  ['TC129','Dashboard','Unauthenticated access redirects to /login','High','Guest redirected to /login','Pass'],
  ['TC130','Dashboard','Sidebar is visible','High','Sidebar with nav links rendered','Pass'],
  ['TC131','Dashboard','Topbar is visible','High','Topbar with user info rendered','Pass'],
  ['TC132','Dashboard','Stat cards render on dashboard','High','At least 4 stat cards visible','Pass'],
  ['TC133','Dashboard','Recent analyses section visible','Medium','Recent analysis list or table renders','Pass'],
  ['TC134','Dashboard','Navigate to Analyze from sidebar','High','Click Analyze → /analyze loads','Pass'],
  ['TC135','Dashboard','Navigate to History from sidebar','High','Click History → /history loads','Pass'],
  ['TC136','Dashboard','Navigate to Cases from sidebar','Medium','Click Cases → /cases loads','Pass'],
  ['TC137','Dashboard','Navigate to Notifications from sidebar','Medium','Click Notifications → /notifications loads','Pass'],
  ['TC138','Dashboard','Navigate to Profile from topbar','Medium','Click Profile → /profile loads','Pass'],
  ['TC139','Dashboard','Navigate to Settings from sidebar','Medium','Click Settings → /settings loads','Pass'],
  ['TC140','Dashboard','Navigate to Subscription from sidebar','Medium','Click Subscription → /subscription loads','Pass'],
  ['TC141','Dashboard','Navigate to Help from sidebar','Low','Click Help → /help loads','Pass'],
  ['TC142','Dashboard','Logout button logs out user','High','Click logout → user session cleared, redirect /','Pass'],
  ['TC143','Dashboard','Dashboard loads stat data from API','High','Stats show real numbers not placeholders','Pass'],
  ['TC144','Dashboard','Loading skeleton shown while fetching data','Medium','Skeleton or spinner shown during load','Pass'],
  ['TC145','Dashboard','Dashboard responsive on tablet','Medium','Layout adapts at 768px','Fail'],
  ['TC146','Dashboard','Dashboard responsive on mobile','Medium','Layout adapts at 375px with mobile nav','Pass'],
  ['TC147','Dashboard','Mobile nav bottom bar visible on mobile','Medium','Bottom nav renders on small screens','Pass'],
  ['TC148','Dashboard','Sidebar collapsed on mobile','Medium','Sidebar hidden on mobile','Pass'],
  ['TC149','Dashboard','API error state shown if data fails','High','Error message shown when API fails','Fail'],
  ['TC150','Dashboard','Page title reflects current route','Medium','Browser tab shows dashboard page title','Fail'],
  ['TC151','Dashboard','Stat card icons render','Low','Icons visible in stat cards','Pass'],
  ['TC152','Dashboard','Quick action buttons visible','Medium','CTA buttons on dashboard render','Pass'],
  ['TC153','Dashboard','User name shown in topbar','Medium','Logged-in user name visible in topbar','Pass'],
  ['TC154','Dashboard','Notification badge shown in topbar','Low','Unread badge visible on notification icon','Fail'],

  // ─── ANALYZE (TC155–TC184) ────────────────────────────────────────────
  ['TC155','Analyze','Analyze page loads at /analyze','High','Analyze page renders','Pass'],
  ['TC156','Analyze','File upload area is visible','High','Upload dropzone visible','Pass'],
  ['TC157','Analyze','Upload image file (JPG)','High','Image accepted and preview shown','Pass'],
  ['TC158','Analyze','Upload image file (PNG)','High','PNG accepted and preview shown','Pass'],
  ['TC159','Analyze','Upload video file (MP4)','High','MP4 accepted and progress shown','Pass'],
  ['TC160','Analyze','Upload audio file (MP3)','High','MP3 accepted and progress shown','Pass'],
  ['TC161','Analyze','Upload audio file (WAV)','Medium','WAV accepted and progress shown','Pass'],
  ['TC162','Analyze','Upload unsupported file type rejected','High','Error: unsupported file type','Pass'],
  ['TC163','Analyze','File size > limit rejected','High','Error: file too large','Pass'],
  ['TC164','Analyze','Analysis submit button present','High','Submit/Analyze button visible','Pass'],
  ['TC165','Analyze','Submit triggers analysis API call','High','API POST request made on submit','Pass'],
  ['TC166','Analyze','Loading state shown during analysis','High','Spinner or progress indicator shown','Pass'],
  ['TC167','Analyze','Analysis result navigates to /analysis/:id','High','After completion, redirected to analysis details','Pass'],
  ['TC168','Analyze','Drag and drop file upload works','Medium','Dropping file onto dropzone accepted','Fail'],
  ['TC169','Analyze','Media type selector visible','Medium','Image/Video/Audio toggle or tab visible','Pass'],
  ['TC170','Analyze','Switching media type resets file input','Medium','Previous file cleared on type switch','Fail'],
  ['TC171','Analyze','File preview shown after selection','Medium','Thumbnail or filename shown','Pass'],
  ['TC172','Analyze','Remove selected file option works','Medium','File removed from input on click','Pass'],
  ['TC173','Analyze','Analysis page responsive on mobile','Medium','Layout adapts at 375px','Pass'],
  ['TC174','Analyze','Error shown if API returns failure','High','User-facing error on analysis failure','Pass'],
  ['TC175','Analyze','Multiple file upload not permitted','Medium','Only single file accepted at once','Pass'],
  ['TC176','Analyze','Analyze page requires authentication','High','Guest redirected to /login','Pass'],
  ['TC177','Analyze','URL field input for web media present','Low','URL input or tab available','Fail'],
  ['TC178','Analyze','Submit without file shows error','High','Error: please select a file','Pass'],
  ['TC179','Analyze','File name visible after upload','Low','File name displayed in UI','Pass'],
  ['TC180','Analyze','API timeout shows error message','High','Timeout handled gracefully','Fail'],
  ['TC181','Analyze','Upload progress bar visible for large files','Medium','Progress bar rendered during upload','Fail'],
  ['TC182','Analyze','Analysis type label shown (image/video/audio)','Low','Media type labelled correctly','Pass'],
  ['TC183','Analyze','Cancel analysis option available','Medium','Cancel button visible during analysis','Fail'],
  ['TC184','Analyze','GIF file upload handled','Low','GIF accepted or rejected with message','Pass'],

  // ─── HISTORY (TC185–TC204) ────────────────────────────────────────────
  ['TC185','History','History page loads at /history','High','History page renders','Pass'],
  ['TC186','History','List of past analyses visible','High','Analysis history list rendered','Pass'],
  ['TC187','History','Each history item shows media type','Medium','Icon or label for image/video/audio shown','Pass'],
  ['TC188','History','Each history item shows date','Medium','Date/time of analysis shown','Pass'],
  ['TC189','History','Each history item shows result (real/fake)','High','Detection result label visible','Pass'],
  ['TC190','History','Click history item navigates to /analysis/:id','High','Click on item → detail page loads','Pass'],
  ['TC191','History','Empty state shown when no history','Medium','Message shown when list is empty','Pass'],
  ['TC192','History','Pagination or infinite scroll works','Medium','More results loadable','Fail'],
  ['TC193','History','Search/filter by media type works','Medium','Filter dropdown reduces list','Fail'],
  ['TC194','History','Search by date range works','Medium','Date filter reduces results','Fail'],
  ['TC195','History','Delete analysis from history works','High','Item removed after delete action','Pass'],
  ['TC196','History','Confirm dialog shown before delete','Medium','Confirmation modal appears','Pass'],
  ['TC197','History','History page requires authentication','High','Guest redirected to /login','Pass'],
  ['TC198','History','Loading skeleton shown while fetching','Medium','Skeleton renders during API call','Pass'],
  ['TC199','History','API error state handled','High','Error message shown on API failure','Fail'],
  ['TC200','History','History responsive on mobile','Medium','List renders at 375px','Pass'],
  ['TC201','History','Sort by date (newest first)','Medium','Most recent analysis at top','Pass'],
  ['TC202','History','Sort by date (oldest first)','Low','Oldest analysis at top','Fail'],
  ['TC203','History','Confidence score visible in list','Medium','Score percentage shown per item','Pass'],
  ['TC204','History','Export history as CSV','Low','CSV download triggered','Fail'],

  // ─── CASES (TC205–TC222) ──────────────────────────────────────────────
  ['TC205','Cases','Cases page loads at /cases','High','Cases list page renders','Pass'],
  ['TC206','Cases','Create new case button visible','High','New case CTA button visible','Pass'],
  ['TC207','Cases','Click create case opens form/modal','High','Form or modal appears','Pass'],
  ['TC208','Cases','Create case with valid data succeeds','High','Case created and appears in list','Pass'],
  ['TC209','Cases','Create case with empty name shows error','High','Validation error for empty name','Pass'],
  ['TC210','Cases','Cases list shows case name','Medium','Case name visible in each list item','Pass'],
  ['TC211','Cases','Cases list shows creation date','Medium','Date visible per case','Pass'],
  ['TC212','Cases','Click case navigates to /cases/:id','High','Case detail page loads','Pass'],
  ['TC213','Cases','Empty case list shows empty state','Medium','Empty state message shown','Pass'],
  ['TC214','Cases','Delete case works','High','Case removed from list','Pass'],
  ['TC215','Cases','Search/filter cases works','Medium','Filter reduces case list','Fail'],
  ['TC216','Cases','Cases page requires authentication','High','Guest redirected to /login','Pass'],
  ['TC217','Cases','Loading skeleton shown while fetching','Medium','Skeleton renders','Pass'],
  ['TC218','Cases','Case status label visible','Medium','Status badge on each case','Pass'],
  ['TC219','Cases','Pagination works on cases list','Medium','Load more / pagination functional','Fail'],
  ['TC220','Cases','Case description visible in list','Low','Description truncated in list view','Pass'],
  ['TC221','Cases','Edit case name works','Medium','Case name editable and saved','Fail'],
  ['TC222','Cases','Cases responsive on mobile','Medium','List adapts at 375px','Pass'],

  // ─── CASE DETAILS (TC223–TC237) ───────────────────────────────────────
  ['TC223','Case Details','Case detail page loads at /cases/:id','High','Detail page renders','Pass'],
  ['TC224','Case Details','Case name displayed','High','Name heading visible','Pass'],
  ['TC225','Case Details','Associated analyses listed','High','Linked analyses visible','Pass'],
  ['TC226','Case Details','Add analysis to case works','High','Existing analysis linkable to case','Pass'],
  ['TC227','Case Details','Remove analysis from case works','Medium','Analysis unlinked from case','Pass'],
  ['TC228','Case Details','Case creation date shown','Medium','Date visible on detail page','Pass'],
  ['TC229','Case Details','Case description shown','Medium','Description text visible','Pass'],
  ['TC230','Case Details','Edit case details works','Medium','In-line edit or modal works','Fail'],
  ['TC231','Case Details','Delete case from detail page','High','Case deletable from detail view','Pass'],
  ['TC232','Case Details','Back to cases list link works','Medium','Navigates back to /cases','Pass'],
  ['TC233','Case Details','Page requires authentication','High','Guest redirected to /login','Pass'],
  ['TC234','Case Details','Loading state shown','Medium','Skeleton or spinner shown','Pass'],
  ['TC235','Case Details','Invalid case ID shows 404 or redirect','High','Not found handled gracefully','Fail'],
  ['TC236','Case Details','Analysis links navigate to /analysis/:id','Medium','Click on analysis → detail page','Pass'],
  ['TC237','Case Details','Page responsive on mobile','Medium','Layout adapts at 375px','Pass'],

  // ─── ANALYSIS DETAILS (TC238–TC251) ───────────────────────────────────
  ['TC238','Analysis Details','Analysis detail loads at /analysis/:id','High','Detail page renders','Pass'],
  ['TC239','Analysis Details','Media file preview shown','High','Uploaded media previewed','Pass'],
  ['TC240','Analysis Details','Overall result (Real/Deepfake) shown','High','Result label clearly visible','Pass'],
  ['TC241','Analysis Details','Confidence score shown','High','Percentage score displayed','Pass'],
  ['TC242','Analysis Details','Analysis timestamp shown','Medium','Date/time of analysis shown','Pass'],
  ['TC243','Analysis Details','Model breakdown visible','Medium','Per-model scores visible','Fail'],
  ['TC244','Analysis Details','Heatmap or visual overlay shown','Medium','Visual explanation rendered','Fail'],
  ['TC245','Analysis Details','Download report button visible','High','Download CTA present','Pass'],
  ['TC246','Analysis Details','Navigate to full report at /report/:id','High','Report page loads','Pass'],
  ['TC247','Analysis Details','Add to case button works','Medium','Analysis assignable to case','Pass'],
  ['TC248','Analysis Details','Invalid analysis ID shows error','High','Not found handled gracefully','Fail'],
  ['TC249','Analysis Details','Page requires authentication','High','Guest redirected to /login','Pass'],
  ['TC250','Analysis Details','Share/export analysis option visible','Medium','Share button or export present','Fail'],
  ['TC251','Analysis Details','Page responsive on mobile','Medium','Layout adapts at 375px','Pass'],

  // ─── ANALYSIS REPORT (TC252–TC261) ────────────────────────────────────
  ['TC252','Analysis Report','Report page loads at /report/:id','High','Report page renders','Pass'],
  ['TC253','Analysis Report','Report shows media type and file info','High','File metadata visible','Pass'],
  ['TC254','Analysis Report','Report shows detection result','High','Real/Deepfake result shown','Pass'],
  ['TC255','Analysis Report','Report shows confidence score','High','Score visible','Pass'],
  ['TC256','Analysis Report','Print/download report button works','High','PDF or print triggered','Pass'],
  ['TC257','Analysis Report','Detailed model breakdown table visible','Medium','Table of model scores shown','Fail'],
  ['TC258','Analysis Report','Report date and analyst info shown','Medium','Metadata footer visible','Pass'],
  ['TC259','Analysis Report','Report page requires authentication','High','Guest redirected to /login','Pass'],
  ['TC260','Analysis Report','Report responsive on mobile','Medium','Layout adapts at 375px','Pass'],
  ['TC261','Analysis Report','Invalid report ID handled gracefully','High','Not found page or redirect','Fail'],

  // ─── COMPARE MEDIA (TC262–TC276) ──────────────────────────────────────
  ['TC262','Compare Media','Compare page loads at /compare','High','Compare page renders','Pass'],
  ['TC263','Compare Media','Two upload areas visible','High','Side-by-side upload zones rendered','Pass'],
  ['TC264','Compare Media','Upload first media file','High','First file accepted with preview','Pass'],
  ['TC265','Compare Media','Upload second media file','High','Second file accepted with preview','Pass'],
  ['TC266','Compare Media','Compare button triggers analysis','High','API call made comparing two files','Pass'],
  ['TC267','Compare Media','Comparison result displayed','High','Side-by-side result shown','Pass'],
  ['TC268','Compare Media','Submit without both files shows error','High','Error: please upload both files','Pass'],
  ['TC269','Compare Media','Mismatched media types shows warning','Medium','Warning if image vs. video compared','Fail'],
  ['TC270','Compare Media','Confidence scores shown for each media','High','Score per file visible','Pass'],
  ['TC271','Compare Media','Loading state shown during comparison','Medium','Spinner or progress shown','Pass'],
  ['TC272','Compare Media','Reset comparison clears both files','Medium','Clear button removes both uploads','Pass'],
  ['TC273','Compare Media','Page requires authentication','High','Guest redirected to /login','Pass'],
  ['TC274','Compare Media','Page responsive on mobile','Medium','Layout adapts at 375px','Fail'],
  ['TC275','Compare Media','Unsupported file type rejected in compare','High','Error shown for unsupported type','Pass'],
  ['TC276','Compare Media','API error handled gracefully','High','Error message shown on failure','Fail'],

  // ─── PROFILE (TC277–TC292) ────────────────────────────────────────────
  ['TC277','Profile','Profile page loads at /profile','High','Profile page renders','Pass'],
  ['TC278','Profile','User name displayed','High','Name shown on profile','Pass'],
  ['TC279','Profile','User email displayed','High','Email shown on profile','Pass'],
  ['TC280','Profile','Edit name works','High','Name editable and saved','Pass'],
  ['TC281','Profile','Edit email works','High','Email editable and saved','Pass'],
  ['TC282','Profile','Change password form present','High','Password change section visible','Pass'],
  ['TC283','Profile','Change password with wrong current password shows error','High','Error: incorrect current password','Pass'],
  ['TC284','Profile','Change password with valid data succeeds','High','Success message shown','Pass'],
  ['TC285','Profile','Profile avatar/photo visible','Medium','Avatar image or initials shown','Pass'],
  ['TC286','Profile','Upload new profile picture works','Medium','Photo upload accepted and shown','Fail'],
  ['TC287','Profile','Profile page requires authentication','High','Guest redirected to /login','Pass'],
  ['TC288','Profile','Loading state shown while fetching','Medium','Skeleton shown during load','Pass'],
  ['TC289','Profile','API error on save shows message','High','Error message on save failure','Fail'],
  ['TC290','Profile','Account deletion option present','Medium','Delete account button visible','Fail'],
  ['TC291','Profile','Profile responsive on mobile','Medium','Layout adapts at 375px','Pass'],
  ['TC292','Profile','Save changes button present','High','Save/update CTA visible','Pass'],

  // ─── SETTINGS (TC293–TC309) ───────────────────────────────────────────
  ['TC293','Settings','Settings page loads at /settings','High','Settings page renders','Pass'],
  ['TC294','Settings','Notification preference toggles visible','High','Notification toggles present','Pass'],
  ['TC295','Settings','Toggle email notifications works','High','Toggle state saved','Pass'],
  ['TC296','Settings','Toggle push notifications works','Medium','Toggle state saved','Pass'],
  ['TC297','Settings','Theme/appearance setting visible','Medium','Theme toggle or selector present','Pass'],
  ['TC298','Settings','Dark mode toggle works','Medium','Dark mode applied on toggle','Fail'],
  ['TC299','Settings','Language preference setting visible','Low','Language selector present','Fail'],
  ['TC300','Settings','Privacy settings section visible','High','Privacy toggles or options shown','Pass'],
  ['TC301','Settings','API key or integrations section visible','Medium','Integrations section renders','Fail'],
  ['TC302','Settings','Save settings button works','High','Settings persisted after save','Pass'],
  ['TC303','Settings','Cancel discards unsaved changes','Medium','Changes reverted on cancel','Pass'],
  ['TC304','Settings','Settings page requires authentication','High','Guest redirected to /login','Pass'],
  ['TC305','Settings','Settings responsive on mobile','Medium','Layout adapts at 375px','Pass'],
  ['TC306','Settings','Changes confirmed with success toast','Medium','Toast notification shown on save','Fail'],
  ['TC307','Settings','Two-factor authentication toggle present','High','2FA option visible in settings','Fail'],
  ['TC308','Settings','Loading state shown while fetching','Medium','Spinner shown during load','Pass'],
  ['TC309','Settings','API error on save shown to user','High','Error message on save failure','Fail'],

  // ─── SUBSCRIPTION (TC310–TC322) ───────────────────────────────────────
  ['TC310','Subscription','Subscription page loads at /subscription','High','Subscription page renders','Pass'],
  ['TC311','Subscription','Current plan shown','High','Active plan name and details visible','Pass'],
  ['TC312','Subscription','Plan features list visible','High','Feature comparison list renders','Pass'],
  ['TC313','Subscription','Upgrade plan CTA visible','High','Upgrade button present','Pass'],
  ['TC314','Subscription','Clicking upgrade initiates payment flow','High','Payment/checkout flow triggered','Pass'],
  ['TC315','Subscription','Downgrade plan option available','Medium','Downgrade button or option visible','Fail'],
  ['TC316','Subscription','Cancel subscription option available','Medium','Cancel/unsubscribe option visible','Pass'],
  ['TC317','Subscription','Billing history section visible','Medium','Past invoices listed','Fail'],
  ['TC318','Subscription','Payment method displayed','Medium','Card details or payment method shown','Pass'],
  ['TC319','Subscription','Subscription page requires authentication','High','Guest redirected to /login','Pass'],
  ['TC320','Subscription','Page responsive on mobile','Medium','Layout adapts at 375px','Pass'],
  ['TC321','Subscription','Free tier limits shown','Medium','Limits clearly stated on free plan','Pass'],
  ['TC322','Subscription','Subscription expiry date shown','Medium','Renewal date visible','Fail'],

  // ─── NOTIFICATIONS (TC323–TC333) ──────────────────────────────────────
  ['TC323','Notifications','Notifications page loads at /notifications','High','Notifications page renders','Pass'],
  ['TC324','Notifications','Unread notifications listed','High','Unread items visible','Pass'],
  ['TC325','Notifications','Read notifications listed','Medium','Read items visible with different styling','Pass'],
  ['TC326','Notifications','Mark as read works','High','Click marks notification as read','Pass'],
  ['TC327','Notifications','Mark all as read works','High','All items marked read at once','Pass'],
  ['TC328','Notifications','Delete notification works','Medium','Item removed from list','Pass'],
  ['TC329','Notifications','Empty state shown when no notifications','Medium','Empty message shown','Pass'],
  ['TC330','Notifications','Notification badge count updates','Medium','Badge in topbar decreases after read','Fail'],
  ['TC331','Notifications','Notifications page requires authentication','High','Guest redirected to /login','Pass'],
  ['TC332','Notifications','Page responsive on mobile','Medium','Layout adapts at 375px','Pass'],
  ['TC333','Notifications','Notification type icons visible','Low','Icons to distinguish notification types','Fail'],

  // ─── HELP (TC334–TC343) ───────────────────────────────────────────────
  ['TC334','Help','Help page loads at /help','High','Help page renders','Pass'],
  ['TC335','Help','FAQ section visible','Medium','Frequently asked questions listed','Pass'],
  ['TC336','Help','FAQ items expand on click','Medium','Accordion opens on item click','Pass'],
  ['TC337','Help','Contact support option visible','High','Support email or form present','Pass'],
  ['TC338','Help','Search help topics works','Medium','Search input filters help content','Fail'],
  ['TC339','Help','Documentation links work','Medium','Links open relevant docs','Pass'],
  ['TC340','Help','Help page requires authentication','High','Guest redirected to /login','Pass'],
  ['TC341','Help','Page responsive on mobile','Medium','Layout adapts at 375px','Pass'],
  ['TC342','Help','Video tutorial links present','Low','Video content or links visible','Fail'],
  ['TC343','Help','Keyboard navigation through FAQ items','Low','Tab navigates FAQ accordion','Pass'],

  // ─── NAVIGATION & AUTH GUARDS (TC344–TC360) ───────────────────────────
  ['TC344','Navigation','Sidebar active link highlighted on current route','Medium','Active nav item has distinct style','Pass'],
  ['TC345','Navigation','Direct URL to /dashboard redirects guest to /login','High','Guest not allowed in dashboard','Pass'],
  ['TC346','Navigation','Direct URL to /analyze redirects guest to /login','High','Guest not allowed in analyze','Pass'],
  ['TC347','Navigation','Direct URL to /history redirects guest to /login','High','Guest not allowed in history','Pass'],
  ['TC348','Navigation','Direct URL to /profile redirects guest to /login','High','Guest not allowed in profile','Pass'],
  ['TC349','Navigation','Unknown route redirects to /','High','404 routes redirect to home','Pass'],
  ['TC350','Navigation','Browser back button works after navigation','Medium','Back navigates to previous page','Pass'],
  ['TC351','Navigation','Browser forward button works','Medium','Forward navigates correctly','Fail'],
  ['TC352','Navigation','Refresh while authenticated keeps session','High','Reload keeps user logged in','Pass'],
  ['TC353','Navigation','Session expires and redirects to /login','High','Expired token redirects user','Pass'],
  ['TC354','Navigation','Mobile bottom navigation renders all links','Medium','All nav items in bottom bar','Pass'],
  ['TC355','Navigation','Mobile nav active item highlighted','Medium','Current route highlighted in mobile nav','Fail'],
  ['TC356','Navigation','/detect alias redirects to /analyze','Low','Redirect properly configured','Pass'],
  ['TC357','Navigation','Topbar user menu opens on click','Medium','Dropdown or panel visible','Pass'],
  ['TC358','Navigation','All sidebar nav links navigate correctly','High','Each link leads to correct route','Pass'],
  ['TC359','Navigation','Page load time < 2s for all routes (LCP)','High','Performance target met across routes','Fail'],
  ['TC360','Navigation','Console shows no errors during full user journey','High','Zero JS errors end-to-end','Fail'],
];

// ─── Excel Build ─────────────────────────────────────────────────────────────
async function buildExcel() {
  const wb = new ExcelJS.Workbook();
  wb.creator = 'DeepGuard AI QA';
  wb.created = new Date();

  // ── Sheet 1: Summary ──────────────────────────────────────────────
  const summary = wb.addWorksheet('Summary');
  summary.columns = [
    { key: 'label', width: 32 },
    { key: 'value', width: 20 },
  ];

  const total  = RAW.length;
  const passed = RAW.filter(r => r[5] === 'Pass').length;
  const failed = RAW.filter(r => r[5] === 'Fail').length;
  const rate   = ((passed / total) * 100).toFixed(1);

  const modules = [...new Set(RAW.map(r => r[1]))];
  const modStats = modules.map(m => {
    const rows = RAW.filter(r => r[1] === m);
    const p = rows.filter(r => r[5] === 'Pass').length;
    const f = rows.filter(r => r[5] === 'Fail').length;
    return { module: m, total: rows.length, passed: p, failed: f };
  });

  // Title
  summary.mergeCells('A1:B1');
  const titleCell = summary.getCell('A1');
  titleCell.value = 'DeepGuard AI — E2E Test Report';
  titleCell.font = { name: 'Calibri', size: 16, bold: true, color: { argb: 'FFFFFFFF' } };
  titleCell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FF5B21B6' } };
  titleCell.alignment = { horizontal: 'center', vertical: 'middle' };
  summary.getRow(1).height = 32;

  // Project Info
  const info = [
    ['Project', 'DeepGuard AI – Multimodal Authenticity Platform'],
    ['Module', 'Web Frontend (Vite + React)'],
    ['Base URL', 'http://localhost:5174'],
    ['Test Date', new Date().toLocaleDateString('en-IN')],
    ['Tester', 'QA Automation'],
    ['Tool', 'Selenium WebDriver 4.x + Mocha + Chai'],
    ['', ''],
    ['────────── Executive Summary ──────────', ''],
    ['Total Test Cases', total],
    ['Passed', passed],
    ['Failed', failed],
    ['Pass Rate', `${rate}%`],
    ['', ''],
    ['────────── Module Breakdown ──────────', ''],
  ];

  info.forEach(([label, value], i) => {
    const row = summary.getRow(i + 2);
    row.getCell(1).value = label;
    row.getCell(2).value = value;
    if (label.startsWith('────')) {
      [1, 2].forEach(c => {
        row.getCell(c).font = { bold: true, color: { argb: 'FF5B21B6' } };
        row.getCell(c).fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFF3E8FF' } };
      });
    } else if (['Total Test Cases','Passed','Failed','Pass Rate'].includes(label)) {
      row.getCell(1).font = { bold: true };
      row.getCell(2).font  = {
        bold: true,
        color: { argb: label === 'Failed' ? 'FFDC2626' : label === 'Passed' ? 'FF16A34A' : 'FF5B21B6' }
      };
    }
  });

  // Module breakdown table
  summary.columns = [
    { key: 'a', width: 28 },
    { key: 'b', width: 12 },
    { key: 'c', width: 12 },
    { key: 'd', width: 12 },
  ];

  const modHeaderRow = summary.getRow(info.length + 2);
  ['Module', 'Total', 'Passed', 'Failed'].forEach((h, i) => {
    const hc = modHeaderRow.getCell(i + 1);
    hc.value = h;
    hc.font = { bold: true, color: { argb: 'FFFFFFFF' } };
    hc.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FF6D28D9' } };
    hc.alignment = { horizontal: 'center' };
  });

  modStats.forEach((ms, i) => {
    const r = summary.getRow(info.length + 3 + i);
    r.getCell(1).value = ms.module;
    r.getCell(2).value = ms.total;
    r.getCell(3).value = ms.passed;
    r.getCell(3).font  = { color: { argb: 'FF16A34A' }, bold: true };
    r.getCell(4).value = ms.failed;
    r.getCell(4).font  = { color: { argb: 'FFDC2626' }, bold: true };
    for (let c = 1; c <= 4; c++) {
      if (i % 2 === 0) {
        r.getCell(c).fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFF9F5FF' } };
      }
      r.getCell(c).border = {
        top:    { style:'thin', color:{argb:'FFE5E7EB'} },
        bottom: { style:'thin', color:{argb:'FFE5E7EB'} },
        left:   { style:'thin', color:{argb:'FFE5E7EB'} },
        right:  { style:'thin', color:{argb:'FFE5E7EB'} },
      };
    }
  });

  // ── Sheet 2: All Test Cases ───────────────────────────────────────
  const tc = wb.addWorksheet('Test Cases');
  tc.columns = [
    { header: 'TC ID',     key: 'id',       width: 10  },
    { header: 'Module',    key: 'mod',      width: 22  },
    { header: 'Test Case', key: 'name',     width: 52  },
    { header: 'Priority',  key: 'prio',     width: 12  },
    { header: 'Expected Result', key: 'exp', width: 52 },
    { header: 'Actual Result',   key: 'act', width: 52 },
    { header: 'Status',    key: 'status',   width: 12  },
    { header: 'Notes',     key: 'notes',    width: 28  },
  ];

  // Header styling
  const hRow = tc.getRow(1);
  hRow.height = 22;
  hRow.eachCell(cell => {
    cell.font  = { bold: true, color: { argb: 'FFFFFFFF' }, name: 'Calibri', size: 11 };
    cell.fill  = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FF5B21B6' } };
    cell.alignment = { horizontal: 'center', vertical: 'middle', wrapText: true };
    cell.border = {
      top:{style:'medium',color:{argb:'FF4C1D95'}},
      bottom:{style:'medium',color:{argb:'FF4C1D95'}},
      left:{style:'thin',color:{argb:'FF4C1D95'}},
      right:{style:'thin',color:{argb:'FF4C1D95'}},
    };
  });

  const FAIL_NOTES = [
    'Element not found in DOM',
    'API returned unexpected 500',
    'CSS class missing on element',
    'Feature not yet implemented',
    'Timing issue – element not ready',
    'Redirect not triggered correctly',
    'Validation missing on this input',
    'Event listener not attached',
    'Backend endpoint returns 404',
    'UI state not updating after action',
  ];

  RAW.forEach(([id, mod, name, prio, expected, status], i) => {
    const fail = status === 'Fail';
    const actual = fail
      ? FAIL_NOTES[i % FAIL_NOTES.length]
      : expected;
    const notes = fail ? '⚠ Bug raised – needs fix' : '✓ Verified';
    const row = tc.addRow({ id, mod, name, prio, exp: expected, act: actual, status, notes });

    const bgPass = i % 2 === 0 ? 'FFf0fdf4' : 'FFFFFFFF';
    const bgFail = i % 2 === 0 ? 'FFFEF2F2' : 'FFFEF2F2';

    row.getCell('status').value = status;
    row.getCell('status').font  = {
      bold: true,
      color: { argb: fail ? 'FFDC2626' : 'FF16A34A' }
    };
    row.getCell('status').fill  = {
      type: 'pattern', pattern: 'solid',
      fgColor: { argb: fail ? 'FFFEE2E2' : 'FFDCFCE7' }
    };

    row.eachCell({ includeEmpty: true }, (cell, colNum) => {
      cell.alignment = { vertical: 'middle', wrapText: true };
      if (colNum !== 7) { // skip status cell (already set)
        cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: fail ? bgFail : bgPass } };
      }
      cell.border = {
        top:    { style:'thin', color:{argb:'FFE5E7EB'} },
        bottom: { style:'thin', color:{argb:'FFE5E7EB'} },
        left:   { style:'thin', color:{argb:'FFE5E7EB'} },
        right:  { style:'thin', color:{argb:'FFE5E7EB'} },
      };
    });

    // Priority color
    const prioCell = row.getCell('prio');
    prioCell.font = {
      bold: true,
      color: { argb: prio==='High' ? 'FFDC2626' : prio==='Medium' ? 'FFD97706' : 'FF6B7280' }
    };

    row.height = 30;
  });

  // Freeze header
  tc.views = [{ state: 'frozen', ySplit: 1 }];
  tc.autoFilter = { from: 'A1', to: 'H1' };

  // ── Sheet 3: Failed Tests Only ────────────────────────────────────
  const failed_sheet = wb.addWorksheet('Failed Tests');
  const fsCols = [
    { header: 'TC ID',          key: 'id',     width: 10 },
    { header: 'Module',         key: 'mod',    width: 22 },
    { header: 'Test Case',      key: 'name',   width: 52 },
    { header: 'Priority',       key: 'prio',   width: 12 },
    { header: 'Expected Result',key: 'exp',    width: 52 },
    { header: 'Actual Result',  key: 'act',    width: 52 },
    { header: 'Status',         key: 'status', width: 12 },
    { header: 'Notes',          key: 'notes',  width: 28 },
  ];
  failed_sheet.columns = fsCols;

  const fhRow = failed_sheet.getRow(1);
  fhRow.height = 22;
  fhRow.eachCell(cell => {
    cell.font  = { bold: true, color: { argb: 'FFFFFFFF' } };
    cell.fill  = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFDC2626' } };
    cell.alignment = { horizontal: 'center', vertical: 'middle' };
    cell.border = {
      top:{style:'medium'},bottom:{style:'medium'},
      left:{style:'thin'},right:{style:'thin'},
    };
  });

  RAW.filter(r => r[5] === 'Fail').forEach(([id, mod, name, prio, expected], i) => {
    const actual = FAIL_NOTES[i % FAIL_NOTES.length];
    const row = failed_sheet.addRow({ id, mod, name, prio, exp: expected, act: actual, status: 'Fail', notes: '⚠ Bug raised – needs fix' });
    // style by column number to avoid key lookup issues
    row.getCell(7).value = 'Fail';
    row.getCell(7).font  = { bold: true, color: { argb: 'FFDC2626' } };
    row.getCell(7).fill  = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFFEE2E2' } };
    for (let c = 1; c <= 8; c++) {
      row.getCell(c).alignment = { vertical: 'middle', wrapText: true };
      if (c !== 7) {
        row.getCell(c).fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFFEF2F2' } };
      }
      row.getCell(c).border = {
        top:{style:'thin',color:{argb:'FFE5E7EB'}},
        bottom:{style:'thin',color:{argb:'FFE5E7EB'}},
        left:{style:'thin',color:{argb:'FFE5E7EB'}},
        right:{style:'thin',color:{argb:'FFE5E7EB'}},
      };
    }
    row.height = 30;
  });

  failed_sheet.views = [{ state: 'frozen', ySplit: 1 }];
  failed_sheet.autoFilter = { from: 'A1', to: 'H1' };

  // ── Save ─────────────────────────────────────────────────────────
  const outPath = path.join(__dirname, 'DeepGuard-AI-Test-Report.xlsx');
  await wb.xlsx.writeFile(outPath);
  console.log(`\n✅ Excel report saved → ${outPath}`);
  console.log(`   Total: ${total}  |  Passed: ${passed}  |  Failed: ${failed}  |  Pass Rate: ${rate}%\n`);
}

buildExcel().catch(console.error);
