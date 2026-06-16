浣犳鍦ㄦ牴鎹綔鑰呭弽棣堜慨璁竴涓皬璇村€欓€夌銆?
閲嶈瑙勫垯锛?- 杩欐槸鐢熸垚鏂扮殑 child candidate锛屼笉鏄慨鏀规寮忔鏂囥€?- 姝ｅ紡姝ｆ枃浜嬪疄閿氱偣涓嶅彲杩濊儗銆?- 鐖跺€欓€夌鏄渶瑕佷慨璁㈢殑鑽夌锛屼笉鏄渶缁堜簨瀹炪€?- 涓嶈鑷姩瑕嗙洊姝ｅ紡姝ｆ枃銆?- 涓嶈鑷姩閲囩敤鍊欓€夌銆?- 涓嶈鏂板閲嶈浜虹墿銆佺粍缁囥€侀亾鍏枫€佸湴鐐广€佹椂闂寸嚎璁惧畾锛岄櫎闈炵敤鎴峰弽棣堟槑纭姹傘€?- 杈撳嚭瀹屾暣淇鍚庣殑鍊欓€夌姝ｆ枃銆?- 涓嶈杈撳嚭瑙ｉ噴銆佽瘎鍒嗐€佸垪琛ㄣ€佹爣棰樿鏄庢垨 Markdown 鍏冧俊鎭€?
銆恠ource_path銆?{{ source_path }}

{% include 'blocks/continuity-anchors.md' %}


銆愭寮忔鏂囦簨瀹為敋鐐广€?{{ official_source_text }}

銆愮埗鍊欓€夌銆?{{ parent_candidate_text }}

銆愮敤鎴峰弽棣堛€?{{ feedback_text }}

{% if quick_actions %}
銆愬揩鎹峰弽棣堛€?{% for action in quick_actions %}
- {{ action }}
{% endfor %}
{% endif %}

銆愪慨鏀硅寖鍥淬€?{{ repair_scope }}

{% if parent_beat_validation_summary %}
銆愮埗鍊欓€夌淇℃伅鐐规鏌ユ憳瑕併€?鐘舵€侊細{{ parent_beat_validation_status }}
鎽樿锛歿{ parent_beat_validation_summary }}
{% endif %}

{% if required_beats %}
銆愬繀椤讳繚鐣欐垨琛ヤ笂鐨勪俊鎭偣銆?{% for beat in required_beats %}
{{ loop.index }}. {{ beat.text }}
{% endfor %}
{% endif %}

{% if forbidden_beats %}
銆愮姝㈠嚭鐜版垨绂佹鎻愬墠鎻檽鐨勫唴瀹广€?{% for beat in forbidden_beats %}
{{ loop.index }}. {{ beat.text }}
{% endfor %}
{% endif %}

璇锋牴鎹敤鎴峰弽棣堜慨璁㈢埗鍊欓€夌銆備慨璁㈡椂浠ユ寮忔鏂囦簨瀹為敋鐐逛负鍑嗭紝淇濈暀宸茬粡婊¤冻鐨勪俊鎭偣锛岃ˉ瓒崇己澶卞唴瀹癸紝骞堕伩鍏嶅紩鍏ユ柊閿欒銆?
鐜板湪鍙緭鍑哄畬鏁翠慨璁㈠悗鐨勫€欓€夌姝ｆ枃銆?
