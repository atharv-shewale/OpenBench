import React, { createContext, useContext, useState, useEffect } from "react";

export const translations = {
  en: {
    // Navigation
    appName: "OpenBench",
    sharedLabs: "Shared Labs",
    discoverEquipment: "Discover Equipment",
    fairnessSimulator: "Fairness Simulator",
    labInventory: "Lab Inventory",
    reviewQueue: "Review Queue",
    listResource: "List Resource",
    dashboard: "Dashboard",
    verifyAudit: "Verify Audit",
    signIn: "Sign In",
    register: "Register",
    signOut: "Sign Out",
    judgeMode: "Judge Mode",
    welcomeCredits: "cr",

    // Home / Hero
    hackathonTag: "48-Hour Open Innovation Hackathon",
    heroTitle: "OpenBench",
    heroMotto: '"Every bench, every hour — earning for science."',
    heroDescription:
      "Safely unlock underused college testing and fabrication labs for local MSMEs, ITI apprentices, and startups using a verified, credit-based booking platform.",
    exploreButton: "Explore Equipment & Spaces",
    managerPortalButton: "Lab Manager Portal",

    // Impact Dashboard
    impactTitle: "OpenBench Collective Impact",
    impactSubtitle: "Quantifying public innovation capacity unlocked from academic institutions.",
    idleHoursUnlocked: "Idle Hours Unlocked",
    equipmentValue: "Equipment Value Utilised",
    estimatedSavings: "Estimated Cost Saved",
    supportedParticipants: "MSMEs & Apprentices Supported",
    estimateNotice: "ALL METRICS LABELLED AS ESTIMATES",
    estimateDisclaimer:
      "Estimated savings and equipment values are benchmarked against standard commercial NABL precision testing rates (₹3,500/hr) vs OpenBench credit pricing.",

    // Judge Journey Steps
    journeyTitle: "Try the Full 10-Step Journey",
    journeySubtitle: "One-click interactive checklist navigating every lifecycle stage of OpenBench.",
    step1: "1. Discover & Check Eligibility",
    step1Desc: "Browse machines, check rules, and inspect 'Am I Eligible?' panel.",
    step2: "2. Request Booking Slot",
    step2Desc: "Submit slot with purpose tier; trigger counterfactual advice if unavailable.",
    step3: "3. Allocation & Why This Outcome?",
    step3Desc: "Inspect waitlist ranking score breakdown and priority boost factors.",
    step4: "4. Manager Queue & Overrides",
    step4Desc: "Review queue with applicant history, approve, reject, or owner override.",
    step5: "5. QR Check-In & Checklist",
    step5Desc: "Verify identity, submit pre-flight checklist and upload before-photo.",
    step6: "6. Machine Activity Simulator",
    step6Desc: "Pulse live telemetry heartbeats and wattage activity to prevent release.",
    step7: "7. Advisory Photo-Diff & Return",
    step7Desc: "Side-by-side condition viewer and advisory OpenCV computer vision diff.",
    step8: "8. Auto-Release & Contestation",
    step8Desc: "Grace period auto-release, proposed strike notice, and user contestation.",
    step9: "9. Shared Timeline & Audit Chain",
    step9Desc: "Review append-only audit trail and test SHA-256 chain verification.",
    step10: "10. Allocation Fairness Simulator",
    step10Desc: "Replay 30-day synthetic demand to prove Gini inequality reduction.",

    // Actions
    tryStep: "Try Step →",
    quickLoginAs: "One-Click Quick Login as:",
    resetDemoData: "Reset Demo Data",
    resetting: "Resetting...",
  },
  mr: {
    // Navigation
    appName: "ओपनबेंच",
    sharedLabs: "सामायिक प्रयोगशाळा",
    discoverEquipment: "उपकरणे शोधा",
    fairnessSimulator: "न्याय्यता सिम्युलेटर",
    labInventory: "लॅब सूची",
    reviewQueue: "पुनरावलोकन रांग",
    listResource: "साधन सूचीबद्ध करा",
    dashboard: "डॅशबोर्ड",
    verifyAudit: "ऑडिट पडताळा",
    signIn: "साइन इन करा",
    register: "नोंदणी करा",
    signOut: "बाहेर पडा",
    judgeMode: "परीक्षक मोड",
    welcomeCredits: "क्रेडिट्स",

    // Home / Hero
    hackathonTag: "४८-तास मुक्त नवकल्पना हॅकाथॉन",
    heroTitle: "ओपनबेंच",
    heroMotto: '"प्रत्येक बेंच, प्रत्येक तास — विज्ञानासाठी सत्कारणी."',
    heroDescription:
      "स्थानिक लघुउद्योग (MSME), ITI प्रशिक्षणार्थी आणि स्टार्टअप्ससाठी महाविद्यालयांमधील अप्रयुक्त चाचणी आणि निर्मिती प्रयोगशाळा सुरक्षितपणे खुल्या करा.",
    exploreButton: "उपकरणे आणि जागा शोधा",
    managerPortalButton: "लॅब व्यवस्थापक पोर्टल",

    // Impact Dashboard
    impactTitle: "ओपनबेंच सामाजिक आणि आर्थिक प्रभाव",
    impactSubtitle: "शैक्षणिक संस्थांमधून अनलॉक केलेल्या सार्वजनिक नवकल्पना क्षमतेचे मोजमाप.",
    idleHoursUnlocked: "अनलॉक केलेले तास",
    equipmentValue: "वापरलेले उपकरण मूल्य",
    estimatedSavings: "अंदाजे केलेली बचत",
    supportedParticipants: "लघुउद्योग आणि प्रशिक्षणार्थी",
    estimateNotice: "सर्व आकडेवारी अंदाजे म्हणून दर्शविली आहे",
    estimateDisclaimer:
      "अंदाजे बचत आणि उपकरणांचे मूल्य व्यावसायिक NABL चाचणी दर (₹३,५००/तास) विरुद्ध ओपनबेंच क्रेडिट दरावर आधारित आहेत.",

    // Judge Journey Steps
    journeyTitle: "पूर्ण १०-टप्प्यांचा प्रवास करून पहा",
    journeySubtitle: "ओपनबेंचच्या प्रत्येक जीवनचक्र टप्प्याची परस्परसंवादी तपासणी सूची.",
    step1: "१. उपकरणे शोधा आणि पात्रता तपासा",
    step1Desc: "मशिन्स तपासा, नियम वाचा आणि 'मी पात्र आहे का?' पॅनल पहा.",
    step2: "२. बुकिंग स्लॉटची विनंती करा",
    step2Desc: "उद्देशासह स्लॉट सबमिट करा; अनुपलब्ध असल्यास पर्यायी सल्ला मिळवा.",
    step3: "३. वाटप आणि परिणामाचे कारण",
    step3Desc: "प्रतीक्षा यादी गुण आणि प्राधान्य घटकांचे विश्लेषण तपासा.",
    step4: "४. व्यवस्थापक रांग आणि मंजुरी",
    step4Desc: "इतिहास तपासा, मंजूर करा, नाकारा किंवा मालक ओव्हरराइड वापरा.",
    step5: "५. QR चेक-इन आणि तपासणी सूची",
    step5Desc: "ओळख पडताळा, सुरुवातीची तपासणी सूची आणि फोटो अपलोड करा.",
    step6: "६. मशीन ॲक्टिव्हिटी सिम्युलेटर",
    step6Desc: "मशीन चालू असल्याचे दर्शवण्यासाठी टेलिमेट्री हार्टबीट पाठवा.",
    step7: "७. सल्लागार फोटो-डिफ आणि परतफेड",
    step7Desc: "समोरासमोर स्थिती तुलना आणि संगणक दृष्टी advisory diff.",
    step8: "८. स्वयं-मुक्तता आणि अपील",
    step8Desc: "वेळेत न आल्यास स्लॉट मुक्ती, प्रस्तावित स्ट्राइक आणि अपील.",
    step9: "९. सामायिक टाइमलाइन आणि ऑडिट पडताळणी",
    step9Desc: "अखंड ऑडिट नोंदवही आणि SHA-256 ब्लॉकचेन पडताळणी तपासा.",
    step10: "१०. वाटप न्याय्यता सिम्युलेटर",
    step10Desc: "Gini विषमता घट सिद्ध करण्यासाठी ३०-दिवसांचे सिम्युलेशन पहा.",

    // Actions
    tryStep: "पहा →",
    quickLoginAs: "एका क्लिकवर लॉगिन करा:",
    resetDemoData: "डेमो डेटा रीसेट करा",
    resetting: "रीसेट होत आहे...",
  },
  hi: {
    // Navigation
    appName: "ओपनबेंच",
    sharedLabs: "साझा प्रयोगशालाएं",
    discoverEquipment: "उपकरण खोजें",
    fairnessSimulator: "निष्पक्षता सिम्युलेटर",
    labInventory: "प्रयोगशाला सूची",
    reviewQueue: "समीक्षा कतार",
    listResource: "संसाधन जोड़ें",
    dashboard: "डैशबोर्ड",
    verifyAudit: "ऑडिट सत्यापित करें",
    signIn: "साइन इन",
    register: "पंजीकरण",
    signOut: "साइन आउट",
    judgeMode: "जज मोड",
    welcomeCredits: "क्रेडिट्स",

    // Home / Hero
    hackathonTag: "48-घंटे का ओपन इनोवेशन हैकाथॉन",
    heroTitle: "ओपनबेंच",
    heroMotto: '"हर बेंच, हर घंटा — विज्ञान के लिए समर्पित।"',
    heroDescription:
      "स्थानीय एमएसएमई (MSME), आईटीआई प्रशिक्षुओं और स्टार्टअप्स के लिए कॉलेज की अप्रयुक्त प्रयोगशालाओं को सुरक्षित और सत्यापित रूप से अनलॉक करें।",
    exploreButton: "उपकरण और लैब देखें",
    managerPortalButton: "लैब प्रबंधक पोर्टल",

    // Impact Dashboard
    impactTitle: "ओपनबेंच सामाजिक व आर्थिक प्रभाव",
    impactSubtitle: "शैक्षणिक संस्थानों से अनलॉक की गई अनुसंधान क्षमता का मूल्यांकन।",
    idleHoursUnlocked: "अनलॉक किए गए घंटे",
    equipmentValue: "उपयोग किया गया उपकरण मूल्य",
    estimatedSavings: "अनुमानित कुल बचत",
    supportedParticipants: "लाभान्वित एमएसएमई व छात्र",
    estimateNotice: "सभी आंकड़े अनुमानित बेंचमार्क हैं",
    estimateDisclaimer:
      "अनुमानित बचत और उपकरण मूल्य मानक वाणिज्यिक NABL परीक्षण दरों (₹3,500/घंटा) बनाम ओपनबेंच क्रेडिट मूल्य पर आधारित हैं।",

    // Judge Journey Steps
    journeyTitle: "संपूर्ण 10-चरणीय यात्रा का अनुभव करें",
    journeySubtitle: "ओपनबेंच के प्रत्येक जीवनचक्र चरण का त्वरित इंटरैक्टिव चेकलिस्ट।",
    step1: "1. उपकरण खोजें और पात्रता जांचें",
    step1Desc: "मशीनें देखें, नियम पढ़ें और 'क्या मैं पात्र हूं?' पैनल देखें।",
    step2: "2. बुकिंग स्लॉट का अनुरोध करें",
    step2Desc: "उद्देश्य के साथ स्लॉट चुनें; उपलब्ध न होने पर अनुशंसित विकल्प देखें।",
    step3: "3. आवंटन और परिणाम का कारण",
    step3Desc: "प्रतीक्षा सूची स्कोर और प्राथमिकता घटकों का विवरण देखें।",
    step4: "4. प्रबंधक समीक्षा और अनुमोदन",
    step4Desc: "उपयोगकर्ता इतिहास देखें, स्वीकृत करें, अस्वीकार करें या ओवरराइड करें।",
    step5: "5. क्यूआर चेक-इन और चेकलिस्ट",
    step5Desc: "पहचान सत्यापित करें, चेकलिस्ट भरें और प्रारंभिक फोटो अपलोड करें।",
    step6: "6. मशीन गतिविधि सिम्युलेटर",
    step6Desc: "मशीन चल रही है यह सिद्ध करने हेतु टेलीमेट्री हार्टबीट भेजें।",
    step7: "7. एडवाइजरी फोटो-डिफ और हैंडओवर",
    step7Desc: "आमने-सामने स्थिति तुलना और एडवाइजरी कंप्यूटर विजन अंतर।",
    step8: "8. स्वतः-मुक्ति और स्ट्राइक अपील",
    step8Desc: "अनुपस्थिति पर स्लॉट स्वतः मुक्त, प्रस्तावित स्ट्राइक और मानवीय अपील।",
    step9: "9. साझा टाइमलाइन और ऑडिट अखंडता",
    step9Desc: "अपरिवर्तनीय ऑडिट ट्रेल और SHA-256 हैश सत्यापन की जांच करें।",
    step10: "10. आवंटन निष्पक्षता सिम्युलेटर",
    step10Desc: "गिनी असमानता में कमी सिद्ध करने के लिए 30-दिवसीय सिमुलेशन देखें।",

    // Actions
    tryStep: "देखें →",
    quickLoginAs: "एक क्लिक में लॉगिन करें:",
    resetDemoData: "डेमो डेटा रीसेट करें",
    resetting: "रीसेट हो रहा है...",
  },
};

const LanguageContext = createContext();

export function LanguageProvider({ children }) {
  const [lang, setLang] = useState(() => {
    return localStorage.getItem("openbench_lang") || "en";
  });

  const changeLanguage = (newLang) => {
    if (translations[newLang]) {
      setLang(newLang);
      localStorage.setItem("openbench_lang", newLang);
    }
  };

  const t = (key) => {
    return translations[lang]?.[key] || translations["en"]?.[key] || key;
  };

  return (
    <LanguageContext.Provider value={{ lang, changeLanguage, t }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  const context = useContext(LanguageContext);
  if (!context) {
    return {
      lang: "en",
      changeLanguage: () => {},
      t: (k) => translations["en"][k] || k,
    };
  }
  return context;
}

