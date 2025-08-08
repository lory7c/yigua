-- Insert core I-Ching hexagrams data
INSERT INTO hexagrams (gua_number, gua_name, gua_name_pinyin, upper_trigram, lower_trigram, binary_code, unicode_symbol, basic_meaning, judgement, category, nature) VALUES
(1, '乾', 'qian', '乾', '乾', '111111', '☰', '天，刚健', '元，亨，利，贞。', '乾宫', '吉'),
(2, '坤', 'kun', '坤', '坤', '000000', '☷', '地，柔顺', '元，亨，利牝马之贞。君子有攸往，先迷后得主，利西南得朋，东北丧朋。安贞，吉。', '坤宫', '吉'),
(3, '屯', 'zhun', '坎', '震', '010001', '☵', '困难，积聚', '元，亨，利，贞，勿用，有攸往，利建侯。', '震宫', '平'),
(4, '蒙', 'meng', '艮', '坎', '100010', '☶', '启蒙，教育', '亨。匪我求童蒙，童蒙求我。初噬告，再三渎，渎则不告。利贞。', '坎宫', '平'),
(5, '需', 'xu', '坎', '乾', '010111', '☵', '等待，需要', '有孚，光亨，贞吉。利涉大川。', '乾宫', '吉'),
(6, '讼', 'song', '乾', '坎', '111010', '☰', '争讼，冲突', '有孚，窒。惕中吉。终凶。利见大人，不利涉大川。', '乾宫', '凶'),
(7, '师', 'shi', '坤', '坎', '000010', '☷', '军队，众人', '贞，丈人，吉无咎。', '坎宫', '平'),
(8, '比', 'bi', '坎', '坤', '010000', '☵', '亲比，团结', '吉。原筮元永贞，无咎。不宁方来，后夫凶。', '坤宫', '吉');

-- Insert corresponding lines for Qian hexagram (乾卦)
INSERT INTO lines (hexagram_id, line_position, line_type, line_text, line_meaning, element) VALUES
(1, 1, 1, '初九：潜龙勿用。', '龙潜在渊，不要轻举妄动，时机未到', '金'),
(1, 2, 1, '九二：见龙在田，利见大人。', '龙出现在田野，利于见到德高望重的人，显露才华', '金'),
(1, 3, 1, '九三：君子终日乾乾，夕惕若厉，无咎。', '君子整日努力不懈，晚上还要警惕，虽危险但无过失', '金'),
(1, 4, 1, '九四：或跃在渊，无咎。', '或者跃起，或者退守深渊，进退自如，无过失', '金'),
(1, 5, 1, '九五：飞龙在天，利见大人。', '飞龙在天空，正当其时，利于见到大人物', '金'),
(1, 6, 1, '上九：亢龙有悔。', '龙飞得过高会有后悔，物极必反', '金');

-- Insert lines for Kun hexagram (坤卦)  
INSERT INTO lines (hexagram_id, line_position, line_type, line_text, line_meaning, element) VALUES
(2, 1, 0, '初六：履霜，坚冰至。', '踩到霜，坚冰即将到来，小事预示大事', '土'),
(2, 2, 0, '六二：直，方，大，不习无不利。', '正直，方正，广大，不用学习就无往不利', '土'),
(2, 3, 0, '六三：含章可贞。或从王事，无成有终。', '蕴含美德可以坚持，或许参与王事，无功但有终', '土'),
(2, 4, 0, '六四：括囊；无咎，无誉。', '收紧口袋，无过失也无荣誉，保持低调', '土'),
(2, 5, 0, '六五：黄裳，元吉。', '黄色衣裳，大吉，居中守正', '土'),
(2, 6, 0, '上六：龙战于野，其血玄黄。', '龙在野外争战，血流遍地，阴极阳生', '土');

-- Insert sample keywords
INSERT INTO keywords_tags (keyword, category, frequency, importance_score, description) VALUES
('天', '自然', 100, 5.0, '代表天空、至高无上、刚健的力量'),
('地', '自然', 95, 5.0, '代表大地、承载、柔顺的德性'),
('龙', '象征', 80, 4.5, '象征帝王、力量、变化、君子'),
('君子', '人物', 90, 4.8, '品德高尚的人，有德行的人'),
('大人', '人物', 70, 4.2, '地位崇高或德高望重的人'),
('乾', '卦名', 85, 4.9, '八卦之首，代表天、刚健、创造'),
('坤', '卦名', 85, 4.9, '八卦之一，代表地、柔顺、承载'),
('刚健', '品质', 60, 4.0, '坚强有力，积极向上'),
('柔顺', '品质', 60, 4.0, '温和顺从，包容承载');

-- Insert sample interpretations
INSERT INTO interpretations (target_type, target_id, author, dynasty, source_book, interpretation_text, interpretation_type, importance_level, is_core_content, keywords) VALUES
('hexagram', 1, '孔子', '春秋', '易传·象传', '乾，健也。刚健中正，纯粹精也。六爻皆奇，纯阳无阴，故曰乾。', '象', 5, 1, '刚健,中正,纯粹,纯阳'),
('hexagram', 1, '王弼', '魏', '周易注', '乾者，天之性也。万物资始，故称父也。', '义', 4, 1, '天性,万物,资始'),
('hexagram', 2, '孔子', '春秋', '易传·象传', '坤，顺也。至柔而动也刚，至静而德方。', '象', 5, 1, '柔顺,动刚,静德'),
('line', 1, '朱熹', '宋', '周易本义', '潜龙勿用，阳在下也。阳气潜藏，未可施用，故戒勿用。', '义', 4, 1, '潜龙,阳气,潜藏,勿用'),
('line', 2, '程颐', '宋', '伊川易传', '见龙在田，德施普也。阳气发见，如龙之在田，德化普及。', '义', 4, 1, '见龙,德施,普及,发见');

-- Insert sample divination case
INSERT INTO divination_cases (case_title, hexagram_id, changing_lines, question_type, question_detail, divination_date, interpretation, actual_result, accuracy_rating, is_verified, tags) VALUES
('创业时机咨询', 1, '1,5', '事业', '准备创业开公司，问时机和前景如何', '2024-01-15', '得乾卦初爻和五爻变，初九潜龙勿用示时机未到需等待，九五飞龙在天示将来必有大成。建议先修炼内功，时机成熟必能一飞冲天。', '确实等了半年后时机成熟成功创业', 5, 1, '创业,时机,等待,成功');