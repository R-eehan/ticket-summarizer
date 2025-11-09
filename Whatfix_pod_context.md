# Whatfix Pod Structure and Responsibilities

## Product Lines
1. **DAP (Digital Adoption Platform)**  
   - Focus: Enable content creation, management, and consumption.

2. **Product Analytics**  
   - Focus: Provide user behavior and engagement insights.

3. **Simulation (Mirror)**  
   - Focus: Simulation-based user training and testing.

## Platform Lines (Tribes)
1. **Runtime Platform**  
   - Focus: Execution of guidance content with relevant context across environments

2. **Developer/Infrastructure Platform**  
   - Focus: Foundational technical services and infrastructure that power the entire Whatfix platform. They keep the lights on. 


## DAP Product Line Pods
### 1. **Content Authoring Platform (CAP)**
   - Comprises of:
     - **Whatfix Dashboard**: Manage content lifecycle, movement across stages(Draft, Ready, Production, Content Translation, Publishing actions, Setup space for other features such as Integrations, Advanced Settings and more
     - **Whatfix Studio**: Low-code browser extension for creating guidance content (flows, tips, beacons, etc.) on any HTML based web application
- Studio is also responsible for all the different configuration options within different content types
- Examples include visibility rules usage & configuration experience, customization of the content you create and so on. 
   - Focus: Content creation and management platformization.

### 2. **Content Management & Maintenance (CMM)**
   - Focus: Enhance content lifecycle management, translation experience, content viewing experience, publishing(Push to Production) workflow, environment mapping and more. 

### 3. **Guidance**
   - Focus: Customizable content consumption experience for end-users.
   - Key Areas: 
     - Theming: Icons, colors, fonts.
     - Pop-ups: Design and behavior
     - Guidance analytics

## Platform Tribes Pods
### Runtime Platform
1. **Workflow Engine**
   - Core Technologies:
     - Element Detection: Patented platform for guidance, Studio, and analytics.
     - Contextualization: Delivers content in web application contexts.
   - Focus: Core technologies for guidance creation and automation.

2. **App Engine**
   - Responsibilities:
     - Application-specific nuances (e.g., scrolling, advanced visibility rules platform).
     - Key Metrics: Optimized scripting time and performance.


# Thematic Overview for NPS Keywords

## 1. Content Creation & Management
   - **Studio**:
     - Content creation and widget configuration (Flows, Smart Tips, Beacons, Pop-ups, Launchers).
     - Branching and merging of content.
     - Enhancements to the creation experience.
   - **CMM**:
     - Content lifecycle management (Draft, Ready, Production).
     - Features like tags and auto-translation for multi-language support.
     - Auto-testing capabilities for validating content.
   - **Multi Formats**:
     - Exporting Whatfix Flows to formats like videos, slideshows, PDFs, and ODF files.

---

## 2. Content Maintenance
   - **Workflow Engine**:
     - Simplifying content maintenance across application releases.
     - Keywords: *reselection, app releases, make it simpler*.
   - **CMM**:
     - Understanding and improving workflows for managing impacted content.
     - Keywords: *improve the workflow, understand impacted content*.

---

## 3. Element Selection & Contextualization Experience
   - **Workflow Engine**:
     - Core element detection and latching.
     - CSS selector capabilities.
     - Smart Context (SC) for contextualized guidance delivery.
     - Reselection and visual cues.

---

## 4. Advanced Targeting & Visibility Rules
   - **App Engine**:
     - Advanced visibility rules, display rules, and targeting capabilities.
     - Custom advanced code (AC) support for unique application requirements.

---

## 5. Integration & Interoperability
   - **Integration Hub**:
     - API communication and webhook enablement.
     - Facilitates integration with third-party applications.

---

## 6. Product Usage Analytics & Insights
   - **Product Analytics**:
     - **Tracking**:
       - Auto-capture of user actions and behaviors.
       - Tracking user attributes for events.
     - **Analysis**:
       - Visualization capabilities like funnel insights and trend insights.
       - Cohort creation for deeper analysis.

---

## 7. Deployment Experience
   - **Deployment**:
     - Issues related to browser extensions.
     - Deployment of Whatfix solutions on target web applications.

---

## 8. Customization & Theming
   - **Guidance**:
     - Theming and customization of content consumption (icons, colors, fonts, etc.).
     - Pop-up design and behavior configuration.
   - **App Engine**:
     - Foundational support for theming through display and visibility rules.

---

## 9. Infrastructure & Performance
   - **Infrastructure**:
     - Enabling or disabling platform features.
     - Performance optimizations and scalability.

---

## 10. Feedback Collection & Surveying
   - **Survey**:
     - Ability to create, manage, and run surveys or polls for end-user feedback.

---

### Notes:
- **Content Maintenance** has emerged as a significant theme and spans across Workflow Engine and CMM pods, with distinct responsibilities and relevant keywords.
- Themes remain cross-functional, as Workflow Engine and CMM often interconnect with other pods to deliver a seamless content maintenance experience.
- This structure allows for flexible mapping of NPS feedback to broader themes, supporting targeted improvements and analysis.
- Themes like **"Content Creation & Management"** are comprehensive and encompass multiple pods and capabilities. 
- **"Platform functionalities"** (e.g., App Engine, Workflow Engine) enable and power the experiences provided by consumer-facing pods (e.g., Studio, Guidance, CMM).
- This structure is designed for flexible and high-level NPS feedback analysis, avoiding rigid one-to-one mapping.