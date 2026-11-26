"""Interface text for the Start here tab, the sidebar and the "What can be done?" box (D24).

English is the source. Hindi and Punjabi were drafted for this project and every one of those strings
needs checking by a native speaker before wider use. Numbers are never written into these strings:
the app fills the {placeholders} from the data.
"""

LANGS = {"en": "English", "hi": "हिंदी", "pa": "ਪੰਜਾਬੀ"}

TEXT = {
    "en": {
        # sidebar
        "app_title": "Heat, Rain & Harvest",
        "app_sub": "District climate risk for wheat and rice in India",
        "lang": "Language",
        "crop": "Crop",
        "crop_wheat": "Wheat (winter crop)",
        "crop_rice": "Rice (monsoon crop)",
        "district": "District (type to search)",
        "warm": "Warming scenario",
        "warm_help": "Every day this much warmer, rainfall unchanged, farming practice unchanged",
        "data_note": "Data: Government of India (Ministry of Agriculture and Farmers Welfare; India Meteorological "
                     "Department), 1997-2022.",
        # start here
        "title": "Heat, rain and harvests in India",
        "lead": "District crop records for 26 seasons (1997-98 to 2022-23) and India Meteorological Department weather "
                "data from 1901, all from Government of India sources. The five figures below are the main results.",
        "c1": "Rise in India's average temperature since 1951. October and November warmed fastest.",
        "c2_big": "{n} fewer",
        "c2": "cold days each winter than in 1951-80 ({old} then, {new} now).",
        "c3": "Change in wheat yield for each 1 °C rise in winter night temperature (95% range {lo} to {hi}).",
        "c4": "of central India's rice seasons were bad years (more than 10% below normal) when the monsoon was well "
              "below normal. In other years: {normal}.",
        "c5": "Change in wheat yield if every day were {warm} °C warmer and farming stayed the same "
              "(95% range {lo} to {hi}). Rice: {rice}.",
        "charts_h": "Trends",
        "ch1_t": "Temperature compared with 1951-80",
        "ch1_s": "Bars: single years. Line: 10-year average.",
        "ch1_y": "°C above 1951-80",
        "ch2_t": "Cold days per winter",
        "ch2_s": "10-year average",
        "ch2_y": "cold days",
        "ch3_t": "Bad {crop} seasons",
        "ch3_s": "Share of India's {crop} area with yields more than 10% below normal",
        "ch3_y": "% of area",
        "ch4_t": "Modelled change at {warm} °C warmer",
        "ch4_s": "Assumes no change in farming practice",
        "ch4_y": "change in yield (%)",
        "crop_w_wheat": "wheat",
        "crop_w_rice": "rice",
        "x_wheat": "Wheat",
        "x_rice": "Rice",
        "why_2014": "rain and hail at harvest",
        "why_2015": "warm, dry winter",
        "why_2005": "very hot February",
        "why_rice": "weak monsoon",
        "findings_h": "What the results show",
        "f1": "**Warm winter nights did the most damage to wheat.** Night temperature showed the clearest link with "
              "lower yields.",
        "f2": "**Irrigation protects rice from drought, but not wheat from heat.** Even well-irrigated Punjab lost "
              "wheat yield in the March 2022 heatwave.",
        "f3": "**Yields still rose over the period**, helped by better varieties and irrigation. Whether that "
              "continues if warming speeds up is an open question.",
        "next": "To look at one district, choose it in the panel on the left and open My district.",
        "caveat": "Weather is one of several reasons yields go up and down; seeds, pests, prices and farming practice "
                  "matter too. Methods and limits are under For experts.",
        # what can be done
        "adv_h": "What can be done?",
        "adv_disclaimer": "General guidance only. Ask your local Krishi Vigyan Kendra for advice for your farm.",
        "adv_source": "Source",
    },
    "hi": {
        "app_title": "गर्मी, बारिश और फ़सल",  # needs human review
        "app_sub": "भारत में गेहूँ और धान पर मौसम का खतरा, ज़िलेवार",  # needs human review
        "lang": "भाषा",  # needs human review
        "crop": "फ़सल",  # needs human review
        "crop_wheat": "गेहूँ (रबी, सर्दियों की फ़सल)",  # needs human review
        "crop_rice": "धान (ख़रीफ़, मानसून की फ़सल)",  # needs human review
        "district": "ज़िला (नाम लिखकर खोजें)",  # needs human review
        "warm": "अगर तापमान इतना बढ़ जाए",  # needs human review
        "warm_help": "हर दिन इतना गर्म, बारिश वही, खेती का तरीका वही",  # needs human review
        "data_note": "आँकड़े: भारत सरकार (कृषि एवं किसान कल्याण मंत्रालय; भारत मौसम विज्ञान विभाग), 1997-2022।",  # needs human review
        "title": "भारत में गर्मी, बारिश और फ़सल",  # needs human review
        "lead": "26 मौसमों (1997-98 से 2022-23) के ज़िलेवार फ़सल आँकड़े और 1901 से भारत मौसम विज्ञान विभाग के मौसम आँकड़े, "
                "सब भारत सरकार के स्रोतों से। नीचे के पाँच आँकड़े मुख्य नतीजे हैं।",  # needs human review
        "c1": "1951 से भारत का औसत तापमान इतना बढ़ा है। सबसे ज़्यादा बढ़ोतरी अक्टूबर और नवंबर में हुई।",  # needs human review
        "c2_big": "{n} दिन कम",  # needs human review
        "c2": "हर सर्दी में ठंडे दिन, 1951-80 के मुकाबले (तब {old}, अब {new})।",  # needs human review
        "c3": "सर्दी की रातें 1 °C गर्म होने पर गेहूँ की पैदावार में बदलाव (95% दायरा {lo} से {hi})।",  # needs human review
        "c4": "मध्य भारत में जब मानसून की बारिश सामान्य से काफ़ी कम रही, तब धान के इतने मौसम खराब रहे (पैदावार सामान्य से "
              "10% से ज़्यादा कम)। बाकी सालों में: {normal}।",  # needs human review
        "c5": "गेहूँ की पैदावार में बदलाव, अगर हर दिन {warm} °C ज़्यादा गर्म हो और खेती का तरीका न बदले "
              "(95% दायरा {lo} से {hi})। धान: {rice}।",  # needs human review
        "charts_h": "रुझान",  # needs human review
        "ch1_t": "1951-80 के मुकाबले तापमान",  # needs human review
        "ch1_s": "खंभे: हर साल। रेखा: 10 साल का औसत।",  # needs human review
        "ch1_y": "°C, 1951-80 से ज़्यादा",  # needs human review
        "ch2_t": "हर सर्दी में ठंडे दिन",  # needs human review
        "ch2_s": "10 साल का औसत",  # needs human review
        "ch2_y": "ठंडे दिन",  # needs human review
        "ch3_t": "{crop} के खराब मौसम",  # needs human review
        "ch3_s": "भारत के {crop} रकबे का हिस्सा जहाँ पैदावार सामान्य से 10% से ज़्यादा कम रही",  # needs human review
        "ch3_y": "रकबे का %",  # needs human review
        "ch4_t": "{warm} °C ज़्यादा गर्मी पर अनुमानित बदलाव",  # needs human review
        "ch4_s": "मान लिया गया है कि खेती का तरीका नहीं बदलता",  # needs human review
        "ch4_y": "पैदावार में बदलाव (%)",  # needs human review
        "crop_w_wheat": "गेहूँ",  # needs human review
        "crop_w_rice": "धान",  # needs human review
        "x_wheat": "गेहूँ",  # needs human review
        "x_rice": "धान",  # needs human review
        "why_2014": "कटाई के समय बारिश और ओले",  # needs human review
        "why_2015": "गर्म और सूखी सर्दी",  # needs human review
        "why_2005": "बहुत गर्म फ़रवरी",  # needs human review
        "why_rice": "कमज़ोर मानसून",  # needs human review
        "findings_h": "नतीजे क्या बताते हैं",  # needs human review
        "f1": "**सर्दी की गर्म रातों ने गेहूँ को सबसे ज़्यादा नुकसान पहुँचाया।** पैदावार घटने का सबसे साफ़ संबंध रात के "
              "तापमान से मिला।",  # needs human review
        "f2": "**सिंचाई धान को सूखे से बचाती है, पर गेहूँ को गर्मी से नहीं।** अच्छी सिंचाई वाले पंजाब में भी मार्च 2022 की लू "
              "में गेहूँ की पैदावार घटी।",  # needs human review
        "f3": "**इस दौरान पैदावार फिर भी बढ़ी**, बेहतर किस्मों और सिंचाई की वजह से। गर्मी तेज़ी से बढ़ी तो यह बढ़त जारी "
              "रहेगी या नहीं, यह अभी खुला सवाल है।",  # needs human review
        "next": "किसी एक ज़िले को देखने के लिए बाईं ओर ज़िला चुनें और ऊपर My district खोलें।",  # needs human review
        "caveat": "पैदावार के उतार-चढ़ाव की कई वजहें हैं; मौसम उनमें से एक है। बीज, कीट, दाम और खेती का तरीका भी मायने "
                  "रखते हैं। तरीका और सीमाएँ For experts में हैं।",  # needs human review
        "adv_h": "क्या किया जा सकता है?",  # needs human review
        "adv_disclaimer": "यह सामान्य जानकारी है। अपने खेत के लिए सलाह अपने कृषि विज्ञान केंद्र से लें।",  # needs human review
        "adv_source": "स्रोत",  # needs human review
    },
    "pa": {
        "app_title": "ਗਰਮੀ, ਮੀਂਹ ਅਤੇ ਫ਼ਸਲ",  # needs human review
        "app_sub": "ਭਾਰਤ ਵਿੱਚ ਕਣਕ ਅਤੇ ਝੋਨੇ ਉੱਤੇ ਮੌਸਮ ਦਾ ਖ਼ਤਰਾ, ਜ਼ਿਲ੍ਹਾਵਾਰ",  # needs human review
        "lang": "ਭਾਸ਼ਾ",  # needs human review
        "crop": "ਫ਼ਸਲ",  # needs human review
        "crop_wheat": "ਕਣਕ (ਹਾੜ੍ਹੀ, ਸਰਦੀਆਂ ਦੀ ਫ਼ਸਲ)",  # needs human review
        "crop_rice": "ਝੋਨਾ (ਸਾਉਣੀ, ਮਾਨਸੂਨ ਦੀ ਫ਼ਸਲ)",  # needs human review
        "district": "ਜ਼ਿਲ੍ਹਾ (ਨਾਂ ਲਿਖ ਕੇ ਲੱਭੋ)",  # needs human review
        "warm": "ਜੇ ਤਾਪਮਾਨ ਇੰਨਾ ਵਧ ਜਾਵੇ",  # needs human review
        "warm_help": "ਹਰ ਦਿਨ ਇੰਨਾ ਗਰਮ, ਮੀਂਹ ਉਹੀ, ਖੇਤੀ ਦਾ ਤਰੀਕਾ ਉਹੀ",  # needs human review
        "data_note": "ਅੰਕੜੇ: ਭਾਰਤ ਸਰਕਾਰ (ਖੇਤੀਬਾੜੀ ਅਤੇ ਕਿਸਾਨ ਭਲਾਈ ਮੰਤਰਾਲਾ; ਭਾਰਤ ਮੌਸਮ ਵਿਗਿਆਨ ਵਿਭਾਗ), 1997-2022।",  # needs human review
        "title": "ਭਾਰਤ ਵਿੱਚ ਗਰਮੀ, ਮੀਂਹ ਅਤੇ ਫ਼ਸਲ",  # needs human review
        "lead": "26 ਮੌਸਮਾਂ (1997-98 ਤੋਂ 2022-23) ਦੇ ਜ਼ਿਲ੍ਹਾਵਾਰ ਫ਼ਸਲ ਅੰਕੜੇ ਅਤੇ 1901 ਤੋਂ ਭਾਰਤ ਮੌਸਮ ਵਿਗਿਆਨ ਵਿਭਾਗ ਦੇ ਮੌਸਮ "
                "ਅੰਕੜੇ, ਸਾਰੇ ਭਾਰਤ ਸਰਕਾਰ ਦੇ ਸਰੋਤਾਂ ਤੋਂ। ਹੇਠਾਂ ਦਿੱਤੇ ਪੰਜ ਅੰਕੜੇ ਮੁੱਖ ਨਤੀਜੇ ਹਨ।",  # needs human review
        "c1": "1951 ਤੋਂ ਭਾਰਤ ਦਾ ਔਸਤ ਤਾਪਮਾਨ ਇੰਨਾ ਵਧਿਆ ਹੈ। ਸਭ ਤੋਂ ਵੱਧ ਵਾਧਾ ਅਕਤੂਬਰ ਅਤੇ ਨਵੰਬਰ ਵਿੱਚ ਹੋਇਆ।",  # needs human review
        "c2_big": "{n} ਦਿਨ ਘੱਟ",  # needs human review
        "c2": "ਹਰ ਸਰਦੀ ਵਿੱਚ ਠੰਢੇ ਦਿਨ, 1951-80 ਦੇ ਮੁਕਾਬਲੇ (ਉਦੋਂ {old}, ਹੁਣ {new})।",  # needs human review
        "c3": "ਸਰਦੀਆਂ ਦੀਆਂ ਰਾਤਾਂ 1 °C ਗਰਮ ਹੋਣ ਨਾਲ ਕਣਕ ਦੇ ਝਾੜ ਵਿੱਚ ਬਦਲਾਅ (95% ਦਾਇਰਾ {lo} ਤੋਂ {hi})।",  # needs human review
        "c4": "ਮੱਧ ਭਾਰਤ ਵਿੱਚ ਜਦੋਂ ਮਾਨਸੂਨ ਦਾ ਮੀਂਹ ਆਮ ਨਾਲੋਂ ਕਾਫ਼ੀ ਘੱਟ ਪਿਆ, ਤਾਂ ਝੋਨੇ ਦੇ ਇੰਨੇ ਮੌਸਮ ਮਾੜੇ ਰਹੇ (ਝਾੜ ਆਮ ਨਾਲੋਂ "
              "10% ਤੋਂ ਵੱਧ ਘੱਟ)। ਬਾਕੀ ਸਾਲਾਂ ਵਿੱਚ: {normal}।",  # needs human review
        "c5": "ਕਣਕ ਦੇ ਝਾੜ ਵਿੱਚ ਬਦਲਾਅ, ਜੇ ਹਰ ਦਿਨ {warm} °C ਵੱਧ ਗਰਮ ਹੋਵੇ ਅਤੇ ਖੇਤੀ ਦਾ ਤਰੀਕਾ ਨਾ ਬਦਲੇ "
              "(95% ਦਾਇਰਾ {lo} ਤੋਂ {hi})। ਝੋਨਾ: {rice}।",  # needs human review
        "charts_h": "ਰੁਝਾਨ",  # needs human review
        "ch1_t": "1951-80 ਦੇ ਮੁਕਾਬਲੇ ਤਾਪਮਾਨ",  # needs human review
        "ch1_s": "ਡੰਡੀਆਂ: ਹਰ ਸਾਲ। ਲਕੀਰ: 10 ਸਾਲ ਦੀ ਔਸਤ।",  # needs human review
        "ch1_y": "°C, 1951-80 ਨਾਲੋਂ ਵੱਧ",  # needs human review
        "ch2_t": "ਹਰ ਸਰਦੀ ਵਿੱਚ ਠੰਢੇ ਦਿਨ",  # needs human review
        "ch2_s": "10 ਸਾਲ ਦੀ ਔਸਤ",  # needs human review
        "ch2_y": "ਠੰਢੇ ਦਿਨ",  # needs human review
        "ch3_t": "{crop} ਦੇ ਮਾੜੇ ਮੌਸਮ",  # needs human review
        "ch3_s": "ਭਾਰਤ ਦੇ {crop} ਰਕਬੇ ਦਾ ਹਿੱਸਾ ਜਿੱਥੇ ਝਾੜ ਆਮ ਨਾਲੋਂ 10% ਤੋਂ ਵੱਧ ਘੱਟ ਰਿਹਾ",  # needs human review
        "ch3_y": "ਰਕਬੇ ਦਾ %",  # needs human review
        "ch4_t": "{warm} °C ਵੱਧ ਗਰਮੀ ਉੱਤੇ ਅੰਦਾਜ਼ਨ ਬਦਲਾਅ",  # needs human review
        "ch4_s": "ਮੰਨਿਆ ਗਿਆ ਹੈ ਕਿ ਖੇਤੀ ਦਾ ਤਰੀਕਾ ਨਹੀਂ ਬਦਲਦਾ",  # needs human review
        "ch4_y": "ਝਾੜ ਵਿੱਚ ਬਦਲਾਅ (%)",  # needs human review
        "crop_w_wheat": "ਕਣਕ",  # needs human review
        "crop_w_rice": "ਝੋਨੇ",  # needs human review
        "x_wheat": "ਕਣਕ",  # needs human review
        "x_rice": "ਝੋਨਾ",  # needs human review
        "why_2014": "ਵਾਢੀ ਵੇਲੇ ਮੀਂਹ ਅਤੇ ਗੜੇ",  # needs human review
        "why_2015": "ਗਰਮ ਅਤੇ ਸੁੱਕੀ ਸਰਦੀ",  # needs human review
        "why_2005": "ਬਹੁਤ ਗਰਮ ਫ਼ਰਵਰੀ",  # needs human review
        "why_rice": "ਕਮਜ਼ੋਰ ਮਾਨਸੂਨ",  # needs human review
        "findings_h": "ਨਤੀਜੇ ਕੀ ਦੱਸਦੇ ਹਨ",  # needs human review
        "f1": "**ਸਰਦੀਆਂ ਦੀਆਂ ਗਰਮ ਰਾਤਾਂ ਨੇ ਕਣਕ ਦਾ ਸਭ ਤੋਂ ਵੱਧ ਨੁਕਸਾਨ ਕੀਤਾ।** ਝਾੜ ਘਟਣ ਦਾ ਸਭ ਤੋਂ ਸਾਫ਼ ਸਬੰਧ ਰਾਤ ਦੇ ਤਾਪਮਾਨ "
              "ਨਾਲ ਮਿਲਿਆ।",  # needs human review
        "f2": "**ਸਿੰਜਾਈ ਝੋਨੇ ਨੂੰ ਸੋਕੇ ਤੋਂ ਬਚਾਉਂਦੀ ਹੈ, ਪਰ ਕਣਕ ਨੂੰ ਗਰਮੀ ਤੋਂ ਨਹੀਂ।** ਚੰਗੀ ਸਿੰਜਾਈ ਵਾਲੇ ਪੰਜਾਬ ਵਿੱਚ ਵੀ ਮਾਰਚ "
              "2022 ਦੀ ਲੂ ਨਾਲ ਕਣਕ ਦਾ ਝਾੜ ਘਟਿਆ।",  # needs human review
        "f3": "**ਇਸ ਸਮੇਂ ਦੌਰਾਨ ਝਾੜ ਫਿਰ ਵੀ ਵਧਿਆ**, ਬਿਹਤਰ ਕਿਸਮਾਂ ਅਤੇ ਸਿੰਜਾਈ ਕਰਕੇ। ਜੇ ਗਰਮੀ ਤੇਜ਼ੀ ਨਾਲ ਵਧੀ ਤਾਂ ਇਹ ਵਾਧਾ ਜਾਰੀ "
              "ਰਹੇਗਾ ਜਾਂ ਨਹੀਂ, ਇਹ ਅਜੇ ਖੁੱਲ੍ਹਾ ਸਵਾਲ ਹੈ।",  # needs human review
        "next": "ਕਿਸੇ ਇੱਕ ਜ਼ਿਲ੍ਹੇ ਨੂੰ ਵੇਖਣ ਲਈ ਖੱਬੇ ਪਾਸੇ ਜ਼ਿਲ੍ਹਾ ਚੁਣੋ ਅਤੇ ਉੱਪਰ My district ਖੋਲ੍ਹੋ।",  # needs human review
        "caveat": "ਝਾੜ ਦੇ ਉਤਰਾਅ-ਚੜ੍ਹਾਅ ਦੇ ਕਈ ਕਾਰਨ ਹਨ; ਮੌਸਮ ਉਨ੍ਹਾਂ ਵਿੱਚੋਂ ਇੱਕ ਹੈ। ਬੀਜ, ਕੀੜੇ, ਭਾਅ ਅਤੇ ਖੇਤੀ ਦਾ ਤਰੀਕਾ ਵੀ ਅਹਿਮ "
                  "ਹਨ। ਤਰੀਕਾ ਅਤੇ ਸੀਮਾਵਾਂ For experts ਵਿੱਚ ਹਨ।",  # needs human review
        "adv_h": "ਕੀ ਕੀਤਾ ਜਾ ਸਕਦਾ ਹੈ?",  # needs human review
        "adv_disclaimer": "ਇਹ ਆਮ ਜਾਣਕਾਰੀ ਹੈ। ਆਪਣੇ ਖੇਤ ਲਈ ਸਲਾਹ ਆਪਣੇ ਕ੍ਰਿਸ਼ੀ ਵਿਗਿਆਨ ਕੇਂਦਰ ਤੋਂ ਲਓ।",  # needs human review
        "adv_source": "ਸਰੋਤ",  # needs human review
    },
}


def tr(lang: str, key: str, **values) -> str:
    """Translated string with {placeholders} filled; falls back to English if a key is missing."""
    s = TEXT.get(lang, TEXT["en"]).get(key, TEXT["en"][key])
    return s.format(**values) if values else s
