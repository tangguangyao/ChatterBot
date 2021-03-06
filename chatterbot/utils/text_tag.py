import re
from acora import AcoraBuilder

Zhejiang = ['北京', '浙江','杭州', '宁波', '温州', '嘉兴', '湖州', '绍兴', '金华', '衢州', '台州', '丽水', '舟山',
            '上城', '下城', '西湖', '拱墅', '江干', '滨江', '余杭', '萧山',
            '富阳', '建德', '临安', '淳安', '桐庐',
            '海曙', '江东', '江北', '北仑', '鄞州', '镇海',
            '慈溪', '余姚', '奉化', '宁海', '象山',
            '辖鹿城','瓯海', '龙湾', '乐清', '瑞安', '洞头', '永嘉', '平阳', '苍南', '文成', '泰顺',
            '朱家角', '遂昌', '开化', '昆山', '泰州', '福州', '上海', '横店', '乌镇',
            '四川', '南浔']

jingdian = ['千岛湖', '解放路', '西湖', '西塘', '灵隐寺', '雷峰塔', '同里古镇', '九堡客运', '海洋世界',
            '宋城', '溪口', '尖峰山', '双龙洞', '杜鹃花', '南尖岩', '油菜花', '云和梯田', '白沙岛',
            '周庄', '普陀山', '三潭印月', '钱塘江', '阿育王寺', '古镇', '鲁迅', '乌将军庙',
            '西栅', '东栅', '桃花岛', '海宁', '西溪湿地', '沈家门渔港', '月湖', '双龙', '东极岛',
            '金沙滩', '雁荡山', '莫干山', '飞来峰', '龙井茶', '好玩', '杭州湾大桥',
            '杭州湾跨海大桥', '杭州湾跨海铁路大桥', '海天一洲', '东站', '西站', '南站', '北站']

locater = ['西湖十景', '六大景区', '价', '便宜', '贵', '走', '逛', '去', '沙滩', '三星', '四星', '五星','3星', '4星', '5星',
            '工艺品', '手工品', '分开', '一起']

Route = [
        # '路线', '路线行程', '攻略', '安排','行程', 
        '景点', '打车', '叫车', '出租车', '门票', '酒店', '汽车站', '火车站', '公交站', '携程', '季节',
        '小吃', '美食', '酒吧', '高铁', '票',
        '客栈', '民宿', '大学', '自驾', '滑雪', '住宿', '住','机场', '萧山机场', '关门', '开门', '费用',
        '帐篷', '联票', '好吃', '餐厅', '购物', '特产', '酒店', '老头儿油爆虾',
        '茅老太臭豆腐', '西餐', '五一', '十一', '国庆', '双休', '周末','时节', '时间', '雨', '夜', '晚上',
        '远', '近', '距离', '位置', '免费', '收费', '本地人家']

data = ['1日', '2日', '3日', '4日', '5日', '6日', '7日', '8日', '9日', '10日',
        '1天', '2天', '3天', '4天', '5天', '6天', '7天', '8天', '9天', '10天',
        '一天', '两天', '三天', '四天', '五天', '六天', '七天', '八天', '九天', '十天',
        '一日', '两日', '三日', '四日', '五日', '六日', '七日', '八日', '九日', '十日']

builder = AcoraBuilder(Zhejiang)
builder.update(jingdian)
builder.update(Route)
builder.update(data)
builder.update(locater)

ac = builder.build()

weight = {}

for kw in Zhejiang:
    weight[kw] = 5

for kw in jingdian:
    weight[kw] = 5

Synonym = {
    # '路线': '行程',
    # '路线行程': '行程',
    # '攻略': '行程',
    # '安排': '行程',

    '打车': '打车',
    '叫车': '打车',
    '出租车': '打车',

    '住宿': '酒店',
    '客栈': '酒店',
    '民宿': '酒店',
    '住': '酒店',

    '小吃': '美食',
    '好吃': '美食',

    '好玩': '景点',

    '十一': '国庆',
    '双休': '周末',

    '1日': '1天',
    '一日': '1天',
    '一天': '1天',

    '2日': '2天',
    '两日': '2天',
    '两天': '2天',

    '3日': '3天',
    '三日': '3天',
    '三天': '3天',

    '4日': '4天',
    '四日': '4天',
    '四天': '4天',

    '6日': '6天',
    '六日': '6天',
    '六天': '6天',

    '杭州湾跨海铁路大桥': '杭州湾大桥',
    '杭州湾跨海大桥': '杭州湾大桥',

    '远': '位置', 
    '近': '位置',
    '距离': '位置',
    '走': '位置',
    '去': '位置',
    '逛': '位置',

    '价': '价格',
    '便宜': '价格',
    '贵': '价格',

    '晚上': '夜',
    '三星': '3星',
    '四星': '4星',
    '五星': '5星',

    '手工品': '工艺品',

    '门票': '票',
    '联票': '票'

}

def get_tag(text):
    tags = []
    for kw, pos in ac.finditer(text):
        if kw in Synonym:
            tags.append(Synonym[kw])
        else:
            tags.append(kw)

    # 去掉重复的tag
    uniquetags = []
    for kw in set(tags):
        uniquetags.append(kw)

    return uniquetags

def get_tag_weight():
    return weight