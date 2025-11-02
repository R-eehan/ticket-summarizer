DAP  
The Whatfix Digital Adoption Platform (DAP) is consistently defined across the support documentation as an interactive solution deployed within software applications to deliver contextual guidance, training, and help directly to end-users. It operates as an overlay, adding a layer of instructional and support content on top of the underlying application interface.

Module: Guidance  
The Guidance Dashboard (together with Studio) is the workspace where authors create, customize, organize, and publish all in-app content, Flows, widgets, styles, tags, and more, for web and desktop applications. It manages the full journey from draft to production and gives authors one place to preview or push experiences live.

* Submodule: Flow \- A step-by-step, on-screen walkthrough that overlays your web app to teach users how to complete a task or achieve an objective.   
* Submodule: Beacons \- Animated visual cues (radial, ripple, speckle, etc.) that grab attention and announce changes or new features inside the application.  
* Submodule: SmartTip \- Contextual tool-tips that surface extra guidance or validation exactly where it’s needed (for example, on complex form fields). They appear on hover or via an “i” icon.  
* Submodule: Launchers \- A persistent, customizable button that lets users open any Whatfix asset, Flow, Pop-up, video or link, whenever they need it, with a single click.  
* Submodule: Blockers \- A feature that prevents users from progressing or submitting data until required steps are completed correctly, ensuring compliance and eliminating downstream errors.  
* Submodule: Triggers \- A rule that fires Whatfix content (e.g., Smart Tip or Flow) automatically when specific conditions in the underlying app are met, such as a value, date or user action, providing timely nudges.  
* Submodule: Multiformat exports \- Option to include SlideShow and Article renditions when exporting an on-premise production package, so one ZIP delivers every supported format.  
* Submodule: CSS Customization \- Advanced (beta) editor that exposes tooltip CSS, giving authors pixel-level control, colors, spacing, shadows, button styling, beyond what the UI allows.  
* Submodule: Branching \- Lets a single Flow split into alternative paths based on user choices or conditions, guiding each user down the steps that match their scenario.  
* Submodule: Font customisation \- A style setting that applies a chosen typeface (from an approved list or the host app’s font) globally to all end-user content and widgets for visual consistency.  
* Submodule: AI CSS \- To enable AI powered CSS customization for Tooltip Templates

Module: CMM {Content maintenance & management}  
Content Lifecycle Management divides every item and widget into Draft, Ready, and Production stages so teams can review, version, move, or roll back content safely. The CLM dashboard lets you filter, bulk-select, and export lists while tracking each unit’s exact stage.

* Submodule: Content management on dashboard – Provides Advanced Search, tag/author/type filters, folders, bulk-select checkboxes and a list view so authors can quickly locate many items and run actions like move, publish, delete or export from one place.  
* Submodule: CLM – Content Lifecycle Management – The dedicated CLM Dashboard tracks every asset across Draft, Ready and Production stages, P2P, Stage movement, archiving content and folders.  
* Submodule: Translation – Built-in workflow that lets you clone any Whatfix content into multiple languages, manage strings in a translation panel, and automatically show end-users the version that matches their locale.  
* Submodule: Autotesting – A premium scheduler that spins up Chrome, runs every Flow on the target app after each release, flags step failures and emails a report so broken guidance is fixed before users see it.  
* Submodule: Tags dashboard experience – Enables authors to create role, page or auto tags, bulk-apply them, filter the list view by tag, and drive segmentation and visibility rules in widgets such as Self Help and Task List.  
* Submodule: Notification Center – A unified feed that logs edits, stage moves and other activity on every piece of content, letting any team member review recent changes from a single panel.

Module: CAP {Content Authoring Platform}  
Whatfix Studio, available as a Chrome/Edge extension and as a desktop editor, is the no-code authoring tool inside CAP. It lets creators capture UI elements and build Flows, Smart Tips, Beacons, Pop-ups, etc., directly on top of the target application before pushing them to the Guidance Dashboard for further management.

* Submodule: Studio & Dashboard IA – Whatfix Studio (a browser plug-in) and the redesigned dashboard share a consistent left-hand menu and grouped folders, making navigation, discovery and creation of Flows, Beacons, Surveys etc intuitive for authors.  
* Submodule: Content editing experience on Studio and Dashboard – The Enhanced Edit Experience lets you modify steps, add branches, tweak Launchers and preview changes inline on both Studio and the dashboard, ensuring parity and reducing context-switching.  
* Submodule: Custom variables – Authors can personalise guidance by inserting placeholders such as {first\_name} or referencing window-level JavaScript variables; these dynamic values fill at runtime and can also power visibility rules for truly contextual content.

Module: Whatfix Hub  
Hub (the “DAP on OS” widget) pins to a user’s desktop and collapses into three end-user workspaces: Explorer (searchable content library), Tasks (personal to-do list), and Feedback (two-way communication to authors). It centralizes cross-app guidance in one floating launcher.

* Submodule: Self help – An in-app side-panel that surfaces a curated library of Flows, videos, articles and more, letting users search or browse contextual help any time without leaving the page.  
* Submodule: Task list – A checklist widget that lists onboarding or change-management tasks, shows progress ticks as each item is done, and nudges users to complete the sequence.   
* Submodule: Pop up – An on-screen modal/card that grabs attention to announce new features, downtime, celebrations or other time-sensitive messages; can include images, GIFs, buttons or links.   
* Submodule: Surveys – Built-in NPS, feedback or custom questionnaires shown inside the product to capture user sentiment and channel the results to analytics for insight-driven improvements.   
* Submodule: Content aggregation – A Whatfix web-crawler that connects external repositories (SharePoint, Confluence, etc.), indexes them and makes deep search results instantly available inside Hub widgets.   
* Submodule: DAP on OS – A system-level desktop application that centralises Whatfix Explorer, Tasks, notifications and organisational resources so employees can access everything directly from their operating system.   
* Submodule: Static Content – Help assets (articles, links, PDFs, videos, images) created entirely in the dashboard, independent of live UI elements, for situations where you can’t capture the underlying app.

Module: Whatfix Mobile

* Submodule: SDK Integration – Adding the Leap library to your native Android, iOS, Flutter, etc. codebase so the app can fetch configurations and render Whatfix in-app experiences at runtime.   
* Submodule: SDK Content Creation – Using Whatfix Mobile Studio/Dashboard to capture screens and build Walkthroughs, Pop-ups, Surveys and other widgets without writing code once the SDK is embedded.   
* Submodule: Wrapper – An alternative for apps where source code isn’t available: wrap a responsive web app in a mobile web-view so Whatfix guidance can overlay EAS tools like Salesforce or Workday.   
* Submodule: Mobile Walkthroughs – Sequential steps (tooltips, highlights, etc.) layered over the app to guide users through a task from start to finish.   
* Submodule: Mobile Surveys – In-app NPS or feedback questionnaires that can be targeted to specific screens or segments, with results analysed in the dashboard.   
* Submodule: Mobile Popups – Attention-grabbing in-app messages, full-screen, bottom-sheet or pop-up, used to announce updates, promotions or urgent information.   
* Submodule: SDK Other Features – Advanced capabilities unlocked by the SDK, including element trigger/termination rules, multilingual audio, event callbacks and other configurable behaviours for richer experiences.   
* Submodule: Mobile Multi Lingual Support – Built-in localisation that lets authors add translations and even set the app locale code so end-users automatically see guidance in their preferred language.

Module: Whatfix Desktop  
A lightweight layer that sits on top of native desktop applications (SAP GUI, Microsoft Teams, Java apps, etc.) and injects the same in-app help you see on the web, Flows, Pop-ups, Beacons, Task Lists, and more. The creator works in Desktop Studio, while end users see the guidance through the Desktop Player, enabling just-in-time onboarding and support without leaving the application.

* Submodule: Desktop segmentation – Page-level segmentation for desktop apps. Authors define “segments” (based on active window, element, role, etc.) so that Self Help, Pop-ups, Beacons, and other widgets appear only on the relevant screen, giving each user a context-appropriate experience.   
* Submodule: Desktop performance – Refers to how quickly the Desktop Player loads guidance and how smoothly it runs. The Player is lightweight (auto-updated to the newest build for speed and bug fixes) and simply requires the recommended 8 GB RAM, multicore CPU, and Windows 10+ to maintain sub-second load times.   
* Submodule: Desktop finder \- Refers to how Whatfix desktop is able to find elements from the target application using UiAutomation or SAP Gui scripting frameworks.  
* Submodule: Desktop Studio installer – The Windows installer that sets up Whatfix Desktop Studio for content creators (Flows, Beacons, etc.).   
* Submodule: Desktop player installer – Installer that deploys the Desktop Player for end users (or creators who need preview). Offers system-level or user-level options, 32-/64-bit selection, and auto-update. If the Player fails after an update, reinstalling it usually resolves the problem.   
* Submodule: Desktop Studio preview mode – A toggle (eye icon or Ctrl \+ Shift \+ P) in Desktop Studio that launches the Player locally so creators can see all widgets, Ready and optionally Draft, exactly as end users will, before pushing to production. 

Module: Whatfix Mirror  
An application-simulation builder that captures live screens of any web app and stitches them into a hyper-realistic, interactive replica. Learners can safely practise tasks in this sandbox while authors overlay Flows, Smart Tips, Pop-ups, and track analytics, delivering hands-on training without the risks of a production system.

* Submodule: Mirror Creation – Capturing a sequence of live-application screens in Whatfix Studio to generate a “Mirror Workflow,” the building-block for simulations that can later be grouped into full Simulations.  
* Submodule: Mirror Dashboard – Central workspace where Account Managers preview, manage, rename, edit, delete, and publish Mirror Workflows and Simulations across stages.  
* Submodule: Mirror Assessment – The Proficiency section of Mirror Dashboard Analytics that grades user performance by tracking completion, abandonment, and unique-user metrics for each Workflow, enabling learning-outcome evaluation.  
* Submodule: Mirror End User – The learner’s experience inside a safe, high-fidelity replica of the live app, with consistent screens, quick loading, and no risk to real data, ideal for hands-on practice.  
* Submodule: Mirror Analytics – Built-in analytics (Usage, Proficiency, Trend Insights) that surface engagement data such as unique users, completion rates, drop-offs, and custom funnels to optimize simulations.  
* Submodule: Mirror Guidance – Ability to layer standard Whatfix guidance (Flows, Task Lists, Smart Tips, Beacons, Pop-ups, etc.) directly on the mirrored screens so users receive in-context help while training.

Product Analytics  
Whatfix Product Analytics (PA) is a suite of tools designed to help organizations understand how users interact with their software applications. Its core purpose is to support data-driven decision-making aimed at enhancing the product experience, increasing user adoption.

Module: Insights

* Submodule: Cohorts \- Dynamic or static groups of users used to compare behaviour across features and time.  
* Submodule: User list \- Static CSV upload of user IDs that becomes a cohort filter.  
* Submodule: Ask whatfixAI \- Natural‑language interface that converts plain‑English questions into Analytics charts.  
* Submodule: Dashboards \- Custom boards composed of Trend, Funnel, or other widgets to track KPIs.  
* Submodule: Trends \- Time‑series charts that show how a metric changes over days, weeks, or months.  
* Submodule: Funnels \- Multi‑step visualisation measuring conversion/drop‑off across a defined process.  
* Submodule: User journeys \- Path analysis that reveals common sequences of events taken by users.  
* Submodule: Summary Insights \- Auto‑generated KPIs such as clicks, play counts, completion percentage.  
* Submodule: Limits \- Requests to raise event, user, or dashboard limits within Analytics.  
* Submodule: Reporting \- Requests for new export formats or scheduled email reports.

Module: Foundation and Capture

* Submodule: User Actions \- Custom, user‑defined events instrumented in the Capture layer to track clicks, page views, or any specific interaction.  
* Submodule: User Identification \- Rules that map login identifiers (email, SSO, UUID) to a unique Analytics user ID for accurate person-level tracking.  
* Submodule: User Unification \- Logic that merges multiple identifiers for the same person into a single analytics profile.  
* Submodule: Reserved Variables \- Pre‑defined variable slots (extra\_1, extra\_2, etc.) used to send additional contextual data with every event.  
* Submodule: User Attributes \- Key‑value metadata (role, plan, region) attached to users for segmentation in Analytics.  
* Submodule: Event Attributes \- Additional contextual fields (URL, button text, screen name) captured alongside each event.

Platform  
Module: Runtime Engine (Workflow Engine \+ App Engine)

* Submodule: App Analysis – Backend process that auto-tests content and evaluates how users navigate the application, helping authors detect breakages and understand real user paths.  
* Submodule: Element Detection / CSS Selector – “Smart Detect” algorithm that locates DOM elements accurately with minimal manual selectors, speeding authoring and reducing failures.  
* Submodule: Diagnostics – Real-time panel, that inspects every step/widget, shows “Found/Not Found” status, and gives actionable fixes before pushing to production.  
* Submodule: Latching – Engine logic that pins Launchers (and similar widgets) to the exact element, accounting for resolution changes and selector uniqueness, so UI cues stay anchored.  
* Submodule: Multi step – Engine support for Flows that target multiple similar elements or cross-page journeys; handles complex completion rules and ensures each step appears in sequence.  
* Submodule: Reselection – Live-edit capability allowing authors to re-pick changed UI elements so existing Flows keep working after application UI updates.  
* Submodule: Smart Context – Patented context engine that auto-segments and shows only relevant content on the right page and step, even starting a Flow mid-stream if the user is already part-way through.  
* Submodule: Step Failure – Detection of cases where a Flow step’s target element isn’t found; surfaces probable causes and guided fixes to maintain Flow continuity.  
* Submodule: Display & Visibility Rules – Rule framework (URL, element, attribute, user, action, etc.) that decides where and when widgets or tooltips appear, ensuring contextual relevance.  
* Submodule: Advanced Visibility Rules – Next-gen dynamic evaluation engine that co-exists with legacy rules, adds richer conditions, and migrates old configurations without disrupting live widgets.  
* Submodule: AC Visibility Rules (AI) \- Enabling AI solution to create advanced visibility rules using prompts  
* Submodule: AC reviewer (AI) \- AI based code reviewer to validate and flag errors in AC Code  
* Submodule: AI-powered element detection (AI) \- Element Detection enhancements and incorporation of AI

Module: UI Platform

* Submodule: Canary \- Canary Deployment/ Rollback strategy for UI modules  
* Submodule: Improved monitoring, alerting, and debuggability of extensions/ JS / end-user modules  
* Submodule: Product Analytics for Deployment and Delivery Statistics  
* Submodule: Improvement in Extension reliability  
* Submodule: Self-serviceability of onboarding workflows (including delivery and deployment methods plus extension installation)  
* Submodule: Performance \- Performance optimization of end-user package (size and latency)

Module: Integrations \+ Platform Services

* Submodule: App Integrations – The Integration Hub screen where admins turn on pre-built or custom connectors (for example, Salesforce) and set how often they run, enabling Whatfix to move data or index external repositories automatically  
* Submodule: User Account Management – The Settings → Teammates area that lets an Account Manager invite or remove users, edit their roles, and generally control access and permissions across all Whatfix dashboards.  
* Submodule: Scheduler – A built-in timing engine that allows authors to define start/end dates, time-zones, and recurring intervals so integrations or widgets (such as Task Lists and Beacons) execute automatically on a chosen schedule.

Module: Labs

* Submodule: AI Assistant \- This will enable AI assistant product capability automates workflow steps on its own and do it on its own  
* Submodule: Enterprise Search \- Search across the KB’s.  
* Submodule: Intent Recognition \- A context-aware NLP layer that analyzes end-user inputs or actions to infer their underlying goals, then proactively recommends relevant guidance or automates subsequent steps. For example, recognizing if a user is trying to create a report, onboarding term events, or troubleshooting a flow, and then suggesting or initiating the ideal next action.