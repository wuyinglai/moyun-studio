import json
from typing import Any

from backend.schemas.lite import LiteIdeaCard, LiteNextOptionCard


OPTION_TEMPLATES = [
    ("当众打脸", "公开场合", "让质疑者当场失态", "更大的后台人物注意到主角。"),
    ("危机反杀", "险境现场", "主角用新能力破局", "敌人背后的真正目标露出一角。"),
    ("收获升级", "资源争夺点", "主角拿到关键奖励", "奖励牵出下一轮争夺。"),
]


FALLBACK_IDEA_BANK: list[LiteIdeaCard] = [
    LiteIdeaCard(
        id="xuanhuan-return",
        title="退婚现场，词条觉醒",
        genre="玄幻",
        one_liner="被当众退婚的废柴少年，觉醒神级词条，反手让全场闭嘴。",
        protagonist_hook="曾经被宗门认定灵根破碎，却能看见万物隐藏词条。",
        core_conflict="未婚妻与内门天才联手羞辱他，宗门长老也站在对面。",
        selling_point="退婚打脸、词条升级、宗门考核连续反转。",
    ),
    LiteIdeaCard(
        id="wuxia-sword",
        title="小捕快拔出禁剑",
        genre="武侠",
        one_liner="边城小捕快误拔禁剑，被迫卷入江湖与朝堂的双重追杀。",
        protagonist_hook="看似油滑怕事，实则记忆力惊人，能复刻见过的招式。",
        core_conflict="名门正派要夺剑，朝廷密探要灭口，旧案真相浮出水面。",
        selling_point="快意恩仇、刀光剑影、朝堂江湖双线压迫。",
    ),
    LiteIdeaCard(
        id="romance-contract",
        title="合约婚姻变真香",
        genre="言情",
        one_liner="她为救家族签下合约婚姻，却发现冷面男主一直在暗中护她。",
        protagonist_hook="事业心强、嘴硬心软，不愿把命运交给任何人。",
        core_conflict="豪门旧怨、事业竞争与误会同时压来，两人互相试探。",
        selling_point="暧昧拉扯、强强对抗、护短真香。",
    ),
    LiteIdeaCard(
        id="xianxia-master",
        title="师尊护短，全宗震动",
        genre="仙侠",
        one_liner="被外门欺辱的小弟子，意外成为闭关师尊唯一亲传。",
        protagonist_hook="天赋平平却心性极稳，能在绝境中看见破局生机。",
        core_conflict="各峰争夺资源，旧敌不服，师尊身份暗藏更大秘密。",
        selling_point="师徒羁绊、宗门打脸、秘境成长。",
    ),
    LiteIdeaCard(
        id="urban-rich",
        title="鉴宝直播翻身",
        genre="都市",
        one_liner="负债青年开直播鉴宝，意外看穿古董气运，从捡漏开始逆袭。",
        protagonist_hook="穷到被房东赶人，却有极强观察力和不服输的劲。",
        core_conflict="同行打压、富二代设局、家人误解同时爆发。",
        selling_point="捡漏暴富、直播打脸、都市逆袭。",
    ),
]


GENRES = ["玄幻", "武侠", "言情", "都市", "仙侠"]


class LiteOptionCardsService:
    """Service for handling Lite story option card parsing and fallback generation."""

    @staticmethod
    def extract_json_payload(raw: str) -> Any:
        """Extract the first JSON object/array from occasionally chatty LLM output."""
        text = raw.strip()
        if "```json" in text:
            text = text.split("```json", 1)[1].split("```", 1)[0].strip()
        elif "```" in text:
            text = text.split("```", 1)[1].split("```", 1)[0].strip()

        decoder = json.JSONDecoder()
        for marker in ("[", "{"):
            start = text.find(marker)
            if start < 0:
                continue
            try:
                data, _ = decoder.raw_decode(text[start:])
                return data
            except json.JSONDecodeError:
                continue
        return json.loads(text)

    @staticmethod
    def parse_option_cards(raw: str, next_label: str) -> list[LiteNextOptionCard]:
        """Parse raw LLM output into LiteNextOptionCard objects."""
        data = LiteOptionCardsService.extract_json_payload(raw)
        if isinstance(data, dict):
            data = data.get("cards", [])
        cards: list[LiteNextOptionCard] = []
        for idx, item in enumerate(data[:3], 1):
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or "").strip()
            scene = str(item.get("scene") or item.get("conflict_upgrade") or item.get("conflict") or "").strip()
            protagonist_desire = str(item.get("protagonist_desire") or item.get("desire") or item.get("goal") or "").strip()
            obstacle = str(item.get("obstacle") or item.get("resistance") or item.get("pressure") or "").strip()
            payoff = str(item.get("payoff") or item.get("beat") or "").strip()
            hook = str(item.get("hook") or "").strip()
            advancement = str(item.get("advancement") or item.get("push") or item.get("progress") or "").strip()
            if title and scene and payoff and hook:
                cards.append(LiteNextOptionCard(
                    id=f"next-{next_label}-{idx}",
                    title=title[:16],
                    beat=payoff[:90],
                    scene=scene[:90],
                    protagonist_desire=protagonist_desire[:90] or "主角要拿到一个可见的阶段性收益。",
                    obstacle=obstacle[:90] or scene[:90],
                    payoff=payoff[:80],
                    hook=hook[:80],
                    advancement=advancement[:90] or "推动冲突升级，并让下一场景有明确接力点。",
                ))
        return cards[:3]

    @staticmethod
    def fallback_next_cards(next_label: str, current_content: str, recent_context: str) -> list[LiteNextOptionCard]:
        """Generate fallback option cards when LLM fails."""
        source = current_content or recent_context
        useful_lines = [
            line.strip(" >-")
            for line in source.splitlines()
            if line.strip() and not line.lstrip().startswith("#") and len(line.strip()) > 8
        ]
        context = " ".join(useful_lines)
        hint = (useful_lines[-1] if useful_lines else context)[:32] or "当前冲突"
        options = [
            ("当场反逼", f"对手借“{hint}”继续施压，把主角逼到众人面前。", "主角要当众守住尊严，并拿回被抢走的话语权。", "对手把旁观者和规矩都变成压力，逼主角低头认错。", "主角抓住对方话里的破绽，当众把主动权夺回来。", "幕后撑腰的人被迫露出一句关键口风。", "完成第一次正面反击，并把矛盾推向幕后人物。"),
            ("旧账翻面", "看似对主角不利的旧账，被对手拿来公开施压。", "主角要证明旧账另有隐情，洗掉眼前的污名。", "旧证据被对手抢先解释，旁观者暂时站在对面。", "主角顺势翻出被忽略的细节，让刚占上风的人反而失态。", "旧账牵出一个更大的交换条件。", "回收一条旧线索，同时制造新的利益交换。"),
            ("战果藏钩", "冲突暂时收束，但旁观者开始重新站队。", "主角要把胜势落成实物奖励，而不是只赢口舌。", "奖励被人暗中设限，拿到它反而会引来更高层注意。", "主角拿到实在奖励，同时让羞辱者付出可见代价。", "奖励里藏着下一场景必须打开的新线索。", "把本场景爽点变成下一场景冲突的燃料。"),
        ]
        return [
            LiteNextOptionCard(
                id=f"next-{next_label}-{idx}",
                title=title,
                beat=payoff,
                scene=scene,
                protagonist_desire=protagonist_desire,
                obstacle=obstacle,
                payoff=payoff,
                hook=hook,
                advancement=advancement,
            )
            for idx, (title, scene, protagonist_desire, obstacle, payoff, hook, advancement) in enumerate(options, 1)
        ]

    @staticmethod
    def rotate_cards(seed: str) -> list[LiteIdeaCard]:
        """Rotate fallback idea cards based on a seed."""
        if not seed:
            return FALLBACK_IDEA_BANK[:5]
        offset = sum(ord(ch) for ch in seed) % len(FALLBACK_IDEA_BANK)
        return (FALLBACK_IDEA_BANK[offset:] + FALLBACK_IDEA_BANK[:offset])[:5]
