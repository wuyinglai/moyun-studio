/**
 * 语义着色 — CodeMirror 6 扩展
 *
 * 为小说内容提供语义级语法高亮：
 * - 对话（「」/「」/""）→ 绿色
 * - 角色名 → 蓝色（从外部传入列表）
 * - 场景/环境描写关键词 → 紫色（如"清晨"、"黄昏"、"屋内"等）
 */
import { StateField, StateEffect, type Extension } from '@codemirror/state'
import {
  Decoration,
  EditorView,
} from '@codemirror/view'
// DecorationSet 是 type-only 导出，Vite 8 esbuild 合并导入时会残留 runtime import
// 用 ReturnType 从 Decoration.set 的返回值推导类型，避免从 @codemirror/view 导入类型
type DecorationSet = ReturnType<typeof Decoration.set>

// ─── 效果 ──────────────────────────────────────────────────────

/** 更新角色名列表 */
export const setCharacterNames = StateEffect.define<string[]>()

/** 更新场景关键词列表 */
export const setSceneKeywords = StateEffect.define<string[]>()

// ─── 默认关键词 ─────────────────────────────────────────────────

const DEFAULT_SCENE_KEYWORDS = [
  '清晨', '黄昏', '黎明', '傍晚', '深夜', '午夜', '破晓',
  '屋内', '屋外', '房间', '大厅', '走廊', '花园', '庭院',
  '街道', '森林', '山间', '河边', '海边', '沙漠', '草原',
  '天空', '阳光', '月光', '星光', '风雨', '云雾', '冰雪',
]

// ─── 装饰样式 ───────────────────────────────────────────────────

const dialogueDeco = Decoration.mark({ class: 'cm-semantic-dialogue' })
const characterDeco = Decoration.mark({ class: 'cm-semantic-character' })
const sceneDeco = Decoration.mark({ class: 'cm-semantic-scene' })

// ─── 正则 ───────────────────────────────────────────────────────

// 中文对话：「...」 或 『...』 或 （...）- 括号内的对话
const CN_QUOTE_RE = /[「『（][^」』）]+[」』）]/g
// 英文对话："..." 或 '...'（但不匹配缩写如 don't）
const EN_QUOTE_RE = /"[^"]+"/g

// ─── 语义着色 StateField ────────────────────────────────────────

export function semanticHighlight(initialCharacters: string[] = []): Extension {
  return StateField.define<DecorationSet>({
    create(): DecorationSet {
      return computeDecorations('', initialCharacters)
    },

    update(deco: DecorationSet, tr) {
      if (!tr.docChanged && !tr.effects.some(e => e.is(setCharacterNames) || e.is(setSceneKeywords))) {
        return deco
      }

      // 获取最新角色名
      let chars = initialCharacters
      for (const effect of tr.effects) {
        if (effect.is(setCharacterNames)) {
          chars = effect.value
        }
      }

      return computeDecorations(tr.state.doc.toString(), chars)
    },

    provide(field): Extension {
      return EditorView.decorations.from(field)
    },
  })
}

// ─── 装饰计算 ───────────────────────────────────────────────────

function computeDecorations(text: string, characterNames: string[]): DecorationSet {
  const decos: ReturnType<Decoration['range']>[] = []

  // 为节省性能，跳过过长文本
  if (text.length > 200_000) {
    return Decoration.none
  }

  // 1) 中文对话
  for (const match of text.matchAll(CN_QUOTE_RE)) {
    const from = match.index!
    const to = from + match[0].length
    decos.push(dialogueDeco.range(from, to))
  }

  // 2) 英文对话
  for (const match of text.matchAll(EN_QUOTE_RE)) {
    const from = match.index!
    const to = from + match[0].length
    decos.push(dialogueDeco.range(from, to))
  }

  // 3) 角色名（优先匹配长名字，避免短名匹配到长名的子串）
  if (characterNames.length > 0) {
    const sorted = [...characterNames].sort((a, b) => b.length - a.length)
    const pattern = new RegExp(sorted.map(n => n.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|'), 'g')
    for (const match of text.matchAll(pattern)) {
      const from = match.index!
      const to = from + match[0].length
      decos.push(characterDeco.range(from, to))
    }
  }

  // 4) 场景关键词（不重叠匹配）
  const scenePattern = new RegExp(DEFAULT_SCENE_KEYWORDS.join('|'), 'g')
  for (const match of text.matchAll(scenePattern)) {
    const from = match.index!
    const to = from + match[0].length
    decos.push(sceneDeco.range(from, to))
  }

  return Decoration.set(decos, true)
}
