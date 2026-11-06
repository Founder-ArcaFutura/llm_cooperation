"""Build and freeze the pre-registered multilingual concept lexicon."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LANGS = ("en", "fr", "es", "ar", "zh")
DOMAINS = {
    "food": {"en":"food systems", "fr":"systèmes alimentaires", "es":"sistemas alimentarios", "ar":"النظم الغذائية", "zh":"粮食系统"},
    "health": {"en":"health care", "fr":"soins de santé", "es":"atención de salud", "ar":"الرعاية الصحية", "zh":"医疗保健"},
    "neighborhood": {"en":"neighborhood life", "fr":"vie de quartier", "es":"vida vecinal", "ar":"الحياة في الأحياء", "zh":"社区生活"},
    "education": {"en":"education", "fr":"éducation", "es":"educación", "ar":"التعليم", "zh":"教育"},
    "transport": {"en":"transport", "fr":"transports", "es":"transporte", "ar":"النقل", "zh":"交通"},
    "emergency": {"en":"emergency response", "fr":"intervention d’urgence", "es":"respuesta ante emergencias", "ar":"الاستجابة للطوارئ", "zh":"应急响应"},
    "environment": {"en":"environmental care", "fr":"protection de l’environnement", "es":"cuidado del medioambiente", "ar":"رعاية البيئة", "zh":"环境保护"},
    "finance": {"en":"household finance", "fr":"finances des ménages", "es":"finanzas del hogar", "ar":"الشؤون المالية للأسر", "zh":"家庭财务"},
    "digital": {"en":"digital infrastructure", "fr":"infrastructure numérique", "es":"infraestructura digital", "ar":"البنية التحتية الرقمية", "zh":"数字基础设施"},
    "commons": {"en":"public spaces", "fr":"espaces publics", "es":"espacios públicos", "ar":"الأماكن العامة", "zh":"公共空间"},
}

# Every row is a matched noun-phrase concept; translated kernels are explicit
# draft renderings, not evidence from independent human translators.
KERNELS = {
"cooperation": [
{"en":"reciprocal assistance","fr":"entraide réciproque","es":"ayuda recíproca","ar":"المساعدة المتبادلة","zh":"互助"},
{"en":"mutual aid","fr":"entraide","es":"ayuda mutua","ar":"المعونة المتبادلة","zh":"相互援助"},
{"en":"shared resource allocation","fr":"répartition partagée des ressources","es":"asignación compartida de recursos","ar":"التوزيع المشترك للموارد","zh":"共享资源分配"},
{"en":"resource pooling","fr":"mise en commun des ressources","es":"puesta en común de recursos","ar":"تجميع الموارد","zh":"资源汇集"},
{"en":"joint planning","fr":"planification conjointe","es":"planificación conjunta","ar":"التخطيط المشترك","zh":"共同规划"},
{"en":"coordinated action","fr":"action coordonnée","es":"acción coordinada","ar":"العمل المنسق","zh":"协调行动"},
{"en":"trust building","fr":"création de confiance","es":"creación de confianza","ar":"بناء الثقة","zh":"建立信任"},
{"en":"collective decision making","fr":"prise de décision collective","es":"toma de decisiones colectivas","ar":"اتخاذ القرار الجماعي","zh":"集体决策"},
{"en":"shared responsibility","fr":"responsabilité partagée","es":"responsabilidad compartida","ar":"المسؤولية المشتركة","zh":"共同责任"},
{"en":"reciprocal exchange","fr":"échange réciproque","es":"intercambio recíproco","ar":"التبادل المتبادل","zh":"互惠交换"},
{"en":"collective protection","fr":"protection collective","es":"protección colectiva","ar":"الحماية الجماعية","zh":"集体保护"},
{"en":"community stewardship","fr":"gestion communautaire","es":"gestión comunitaria","ar":"الرعاية المجتمعية","zh":"社区共管"},
{"en":"public goods provision","fr":"fourniture de biens publics","es":"provisión de bienes públicos","ar":"توفير المنافع العامة","zh":"公共产品供给"},
{"en":"joint problem solving","fr":"résolution conjointe de problèmes","es":"resolución conjunta de problemas","ar":"حل المشكلات بشكل مشترك","zh":"共同解决问题"},
{"en":"coalition building","fr":"formation de coalitions","es":"formación de coaliciones","ar":"بناء التحالفات","zh":"建立联盟"}],
"competition_exploitation": [
{"en":"resource hoarding","fr":"accaparement des ressources","es":"acaparamiento de recursos","ar":"احتكار الموارد","zh":"囤积资源"},
{"en":"one-sided extraction","fr":"extraction unilatérale","es":"extracción unilateral","ar":"استخراج أحادي الجانب","zh":"单方面攫取"},
{"en":"competitive bidding","fr":"enchères concurrentielles","es":"licitación competitiva","ar":"المزايدة التنافسية","zh":"竞标"},
{"en":"market capture","fr":"captation du marché","es":"captura del mercado","ar":"الاستحواذ على السوق","zh":"市场控制"},
{"en":"free riding","fr":"passager clandestin","es":"aprovechamiento gratuito","ar":"الانتفاع دون مساهمة","zh":"搭便车"},
{"en":"predatory pricing","fr":"prix prédateurs","es":"precios predatorios","ar":"التسعير الافتراسي","zh":"掠夺性定价"},
{"en":"exclusive control","fr":"contrôle exclusif","es":"control exclusivo","ar":"السيطرة الحصرية","zh":"排他性控制"},
{"en":"strategic withholding","fr":"rétention stratégique","es":"retención estratégica","ar":"الحجب الاستراتيجي","zh":"策略性扣留"},
{"en":"competitive ranking","fr":"classement concurrentiel","es":"clasificación competitiva","ar":"التصنيف التنافسي","zh":"竞争排名"},
{"en":"bargaining leverage","fr":"rapport de force dans la négociation","es":"poder de negociación","ar":"النفوذ التفاوضي","zh":"谈判筹码"},
{"en":"monopoly seeking","fr":"recherche du monopole","es":"búsqueda del monopolio","ar":"السعي إلى الاحتكار","zh":"追求垄断"},
{"en":"opportunistic defection","fr":"défection opportuniste","es":"deserción oportunista","ar":"الانشقاق الانتهازي","zh":"机会主义背离"},
{"en":"rent extraction","fr":"extraction de rente","es":"extracción de rentas","ar":"استخراج الريع","zh":"攫取租金"},
{"en":"discriminatory access","fr":"accès discriminatoire","es":"acceso discriminatorio","ar":"الوصول التمييزي","zh":"歧视性准入"},
{"en":"turf guarding","fr":"défense de pré carré","es":"defensa del territorio propio","ar":"حماية مناطق النفوذ","zh":"守护地盘"}],
"independent_action": [
{"en":"individual planning","fr":"planification individuelle","es":"planificación individual","ar":"التخطيط الفردي","zh":"个人规划"},
{"en":"self provision","fr":"autoproduction","es":"autoabastecimiento","ar":"الاكتفاء الذاتي","zh":"自给自足"},
{"en":"personal budgeting","fr":"budget personnel","es":"presupuesto personal","ar":"الميزانية الشخصية","zh":"个人预算"},
{"en":"solo travel","fr":"voyage en solitaire","es":"viaje en solitario","ar":"السفر منفرداً","zh":"独自旅行"},
{"en":"private study","fr":"étude individuelle","es":"estudio individual","ar":"الدراسة الفردية","zh":"自主学习"},
{"en":"personal exercise","fr":"exercice individuel","es":"ejercicio individual","ar":"التمرين الشخصي","zh":"个人锻炼"},
{"en":"independent repair","fr":"réparation autonome","es":"reparación independiente","ar":"الإصلاح الذاتي","zh":"独立维修"},
{"en":"individual gardening","fr":"jardinage individuel","es":"jardinería individual","ar":"البستنة الفردية","zh":"个人园艺"},
{"en":"private purchasing","fr":"achat individuel","es":"compra individual","ar":"الشراء الفردي","zh":"个人购物"},
{"en":"solo practice","fr":"entraînement en solo","es":"práctica en solitario","ar":"التدرب منفرداً","zh":"独自练习"},
{"en":"personal record keeping","fr":"tenue de registres personnels","es":"registro personal","ar":"حفظ السجلات الشخصية","zh":"个人记账"},
{"en":"independent navigation","fr":"navigation autonome","es":"navegación independiente","ar":"الملاحة المستقلة","zh":"自主导航"},
{"en":"individual volunteering","fr":"bénévolat individuel","es":"voluntariado individual","ar":"التطوع الفردي","zh":"个人志愿服务"},
{"en":"private problem solving","fr":"résolution individuelle de problèmes","es":"resolución individual de problemas","ar":"حل المشكلات بشكل فردي","zh":"独立解决问题"},
{"en":"personal maintenance","fr":"entretien personnel","es":"mantenimiento personal","ar":"الصيانة الشخصية","zh":"个人维护"}],
"neutral_activity": [
{"en":"routine food preparation","fr":"préparation habituelle des aliments","es":"preparación rutinaria de alimentos","ar":"إعداد الطعام المعتاد","zh":"日常备餐"},
{"en":"routine health screening","fr":"dépistage médical courant","es":"examen médico rutinario","ar":"الفحص الصحي الروتيني","zh":"常规健康筛查"},
{"en":"street photography","fr":"photographie de rue","es":"fotografía callejera","ar":"التصوير في الشوارع","zh":"街头摄影"},
{"en":"classroom note taking","fr":"prise de notes en classe","es":"toma de apuntes en clase","ar":"تدوين الملاحظات في الصف","zh":"课堂笔记"},
{"en":"commuter ticket purchase","fr":"achat de billet de transport","es":"compra de billete de transporte","ar":"شراء تذكرة النقل","zh":"购买通勤车票"},
{"en":"weather observation","fr":"observation météorologique","es":"observación del tiempo","ar":"رصد الطقس","zh":"天气观测"},
{"en":"seasonal planting","fr":"plantation saisonnière","es":"siembra estacional","ar":"الزراعة الموسمية","zh":"季节性种植"},
{"en":"routine bill payment","fr":"paiement courant des factures","es":"pago rutinario de facturas","ar":"دفع الفواتير المعتاد","zh":"日常缴费"},
{"en":"software installation","fr":"installation de logiciels","es":"instalación de programas","ar":"تثبيت البرامج","zh":"安装软件"},
{"en":"park photography","fr":"photographie de parc","es":"fotografía de parques","ar":"التصوير في الحدائق","zh":"公园摄影"},
{"en":"package delivery","fr":"livraison de colis","es":"entrega de paquetes","ar":"توصيل الطرود","zh":"包裹递送"},
{"en":"household inventory","fr":"inventaire du foyer","es":"inventario doméstico","ar":"جرد المنزل","zh":"家庭盘点"},
{"en":"calendar scheduling","fr":"planification du calendrier","es":"organización del calendario","ar":"تنظيم التقويم","zh":"日程安排"},
{"en":"routine equipment cleaning","fr":"nettoyage courant du matériel","es":"limpieza rutinaria del equipo","ar":"تنظيف المعدات المعتاد","zh":"日常设备清洁"},
{"en":"local map reading","fr":"lecture de carte locale","es":"lectura de mapas locales","ar":"قراءة الخرائط المحلية","zh":"阅读本地地图"}],
}

def build() -> list[dict]:
    rows = []
    for category, kernels in KERNELS.items():
        assert len(kernels) == 15
        for di, (domain, domain_names) in enumerate(DOMAINS.items()):
            for ki, kernel in enumerate(kernels):
                cid = f"{category[:3].upper()}-{di+1:02d}-{ki+1:02d}"
                # Add matched domain context so concepts remain distinct across domains.
                terms = {
                    "en": f"{kernel['en']} in {domain_names['en']}",
                    "fr": f"{kernel['fr']} dans {domain_names['fr']}",
                    "es": f"{kernel['es']} en {domain_names['es']}",
                    "ar": f"{kernel['ar']} في {domain_names['ar']}",
                    "zh": f"{domain_names['zh']}中的{kernel['zh']}",
                }
                rows.append({
                    "concept_id": cid, "category": category, "domain": domain,
                    "part_of_speech": "noun_phrase", "terms": terms,
                    "translation_provenance": "researcher-authored compositional draft; not independently translated",
                    "translation_review": {lang: ("source" if lang == "en" else "human_review_required") for lang in LANGS},
                    "ambiguity_flag": {lang: (False if lang == "en" else None) for lang in LANGS},
                })
    return rows

def main() -> None:
    rows = build()
    out = ROOT / "lexicon_frozen.json"
    payload = (json.dumps(rows, ensure_ascii=False, indent=2) + "\n").encode()
    out.write_bytes(payload)
    manifest = {
        "experiment": "cooperative_lexical_geometry_v1",
        "lexicon_sha256": hashlib.sha256(payload).hexdigest(),
        "concept_count": len(rows), "per_category": 150, "languages": LANGS,
        "status": "frozen_before_embeddings; target-language drafts require fluent human review",
        "sampling_note": "10 domains x 15 matched noun-phrase frames per category; kernels reused across domains",
    }
    (ROOT / "lexicon_freeze.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))

if __name__ == "__main__": main()
