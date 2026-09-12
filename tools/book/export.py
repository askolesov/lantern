#!/usr/bin/env python3
"""Split src/condensed.json (written by condense.py) into per-chapter story packages:
  NN/node.yaml (only created if missing, so `hidden:` edits survive), NN/text.json, NN/scenes.json,
  NN/cover.jpg (copied from the first scene if missing). Run from the package dir
  (lantern-content/books/hobbit). The scene order/captions used to live in build.py."""
import json, os, pathlib, shutil
scenes={
0:[("bagend","Норка Бильбо"),("hall","Внутри норки"),("hobbit_feet","Хоббит"),("bilbo_father","Родители Бильбо"),("bilbo_pipe","Бильбо пускает колечки дыма"),("gandalf_arrives","Гэндальф приходит в гости"),("gandalf_fireworks","Фейерверки Гэндальфа"),("scratch_door","Знак на двери"),("dwalin","Первый гость — Двалин"),("cakes","Кладовая пустеет"),("more_dwarves","Гномы валятся в дверь"),("dwarves_door","Гномы у круглой двери"),("thorin","Торин Дубощит"),("tea_party","Чаепитие с гномами"),("washing_up","Гномы моют посуду"),("pipes","Колечки дыма"),("dragon_song","Песня о драконе"),("bilbo_scared","Бильбо испугался"),("fireplace_talk","Разговор у камина"),("bilbo_burglar","«Я — взломщик!»"),("map","Карта Горы"),("lonely_mountain","Одинокая Гора и дракон"),("bilbo_bed","Бильбо засыпает")],
1:[("messy_kitchen","Утро после гостей"),("note","Записка на камине"),("leaving","Бильбо бежит без шляпы"),("inn","Встреча в трактире"),("ponies","В путь на пони"),("green_hills","Зелёные холмы"),("rain","Дождь в дороге"),("wet_camp","Мокрая стоянка"),("fire_light","Огонёк в лесу"),("trolls","Три тролля у костра"),("bilbo_sneak","Бильбо крадётся"),("bilbo_purse","Говорящий кошелёк"),("troll_pocket","Тролль поймал хоббита"),("trolls_fight","Тролли дерутся"),("dwarves_sacks","Гномы в мешках"),("gandalf_voice","Тролли спорят до рассвета"),("dawn","Рассвет"),("stone_trolls","Тролли стали камнями"),("troll_cave","Пещера троллей"),("swords","Древние мечи"),("gold_pots","Клад под деревом")],
2:[("river_ford","Через реку"),("mountains","Горы впереди"),("far_mountains","Через пустоши"),("valley_path","Тропа в долину"),("elves_singing","Эльфы поют в деревьях"),("elf_talk","Бильбо и эльф"),("rivendell","Долина Ривенделл"),("last_homely_house","Последний Домашний Приют"),("midsummer_eve","Праздник середины лета"),("elrond","Элронд смотрит на мечи"),("moon_letters","Лунные буквы"),("leaving_rivendell","Снова в путь")],
3:[('climbing_ponies','Вверх в горы на пони'),('storm_giants','Гроза и каменные великаны'),('cave_smoke_rings','Колечки дыма в пещере'),('crack_opens','Стена раскрылась'),('goblin_hall','Зал гоблинов'),('orcrist_revealed','Великий Гоблин узнал меч'),('glamdring_strike','Меч в темноте'),('running_tunnels','Бегство по туннелям'),('two_swords_corner','Гэндальф и Торин у поворота'),('dori_grabbed','Бильбо упал')],
4:[('finds_ring','Кольцо в темноте'),('gollum_lake','Голлум на озере'),('riddle_game','Игра в загадки'),('fish_jumps','Рыба!'),('pocket_question','Что у меня в кармане?'),('three_guesses','Три попытки'),('lost_precious','Пропало!'),('gollum_blocks','Голлум у выхода'),('the_leap','Прыжок'),('stuck_in_door','Застрял в двери'),('buttons_fly','Пуговицы врассыпную')],
5:[('balin_watch','Балин в дозоре'),('burglar_appears','А вот и взломщик!'),('scree_slide','Вниз по осыпи'),('dwarves_in_trees','Гномы на деревьях'),('dori_lifts_bilbo','Дори выручает'),('fire_cones','Горящие шишки'),('goblin_fire_song','Песня гоблинов'),('eagle_snatches_gandalf','Орёл спасает Гэндальфа'),('hanging_from_dori','На ножках Дори'),('eagle_lord_talks','Повелитель орлов'),('ledge_supper','Ужин на уступе')],
6:[('eagle_ride','На спине орла'),('bee_meadow','Пчёлы Беорна'),('beorn_axe','Беорн'),('dwarves_by_twos','Гномы по двое'),('bombur_last','Бомбур последний'),('animal_servants','Слуги-животные'),('night_growl','Ночной рык'),('beorn_warning','Совет Беорна'),('riding_bear_follows','Медведь следом'),('ponies_home','Пони уходят домой'),('gandalf_farewell','Не сходите с тропинки!')],
7:[('eyes_in_dark','Глаза в темноте'),('deer_leap','Олень'),('butterflies','Чёрные бабочки'),('elf_feast','Пир эльфов'),('elvenking_feast','Король эльфов'),('bilbo_vs_spider','Бильбо и паук'),('cocoons','Гномы в коконах'),('stones_and_song','Камни и дразнилка'),('battle_under_tree','Битва с пауками'),('bilbo_vanishes','Бильбо исчезает'),('thorin_before_king','Торин у короля'),('thorin_cell','Торин в темнице')],
8:[('bridge_gate','Через мост'),('balin_before_king','Балин и Король'),('keyhole','Через замочную скважину'),('cellar_trapdoor','Погреб и люк'),('keys','Ключи'),('thorin_freed','Торин на свободе'),('into_barrels','В бочки!'),('last_barrel','Последняя бочка'),('riding_barrel','Верхом на бочке'),('bilbo_sneeze','Апчхи!'),('raft_dawn','Плот на рассвете')],
9:[('long_lake','Долгое озеро'),('laketown','Эсгарот'),('barrels_shore','Бочки на берегу'),('bilbo_opens','Бильбо открывает бочки'),('wet_dwarves','Мокрые гномы'),('bridge_guards','Стража у моста'),('master_feast','Пир у Бургомистра'),('town_cheers','Город ликует'),('old_songs','Старые песни'),('dwarves_fine','Новые наряды'),('bilbo_cold_town','Бильбо простудился'),('boats_loaded','Лодки готовы'),('departure','Отплытие'),('mountain_ahead','К Горе')],
}

chs = json.load(open("src/condensed.json"))
for i, ch in enumerate(chs):
    d = pathlib.Path(f"{i+1:02d}"); d.mkdir(exist_ok=True); (d / "img").mkdir(exist_ok=True)
    json.dump(ch["paras"], open(d / "text.json", "w"), ensure_ascii=False, indent=0)
    sc = [{"img": f, "caption": c} for f, c in scenes.get(i, [])]
    json.dump(sc, open(d / "scenes.json", "w"), ensure_ascii=False, indent=0)
    if not (d / "node.yaml").exists():
        (d / "node.yaml").write_text(f'type: story\ntitle: {ch["title"]}\nlabel: {ch["num"]}\ntext: text.json\nscenes: scenes.json\nimages: img\n')
    first = d / "img" / (sc[0]["img"] + ".jpg") if sc else None
    if first and first.exists() and not (d / "cover.jpg").exists():
        shutil.copy(first, d / "cover.jpg")
    print(d, ch["num"], ch["title"], len(ch["paras"]), "paras", len(sc), "scenes", "" if first and first.exists() else "(no pictures)")
