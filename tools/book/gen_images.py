#!/usr/bin/env python3
"""Generate storybook illustrations for chapters of The Hobbit via OpenAI gpt-image-1.
Usage: OPENAI_API_KEY=... python3 gen_images.py
"""
import base64, json, os, sys, urllib.request, concurrent.futures, pathlib

# Backends: OPENAI_API_KEY -> api.openai.com gpt-image-1 (original); otherwise OPENROUTER_API_KEY ->
# openrouter.ai chat completions with an image-output model (added 2026-09-04; key lives in
# life/dossiers/2026-08-local-ai-hardware/.env, source it before running — never copy it into this repo).
KEY = os.environ.get("OPENAI_API_KEY"); BACKEND = "openai"
if not KEY:
    KEY = os.environ.get("OPENROUTER_API_KEY"); BACKEND = "openrouter"
if not KEY:
    sys.exit("OPENAI_API_KEY or OPENROUTER_API_KEY not set")
OR_MODEL = os.environ.get("OR_MODEL", "openai/gpt-5-image")
ONLY = sys.argv[1:]   # optional: scene names to generate (e.g. `python3 gen_images.py 04_climbing_ponies`)

# Old prefix, used for ch. 1-6 (cute, toddler-ish). Kept for reference; do NOT use for new images.
BASE_OLD = ("Warm, cozy children's picture-book illustration, soft watercolor and ink, gentle colors, friendly rounded "
            "characters, no text, no letters. Only the characters mentioned in the scene are shown. "
            "Everything friendly and gentle, suitable for a 4-year-old. ")

# Current prefix (user decision 2026-09-02): realistic storybook drawing for a 4-year-old, not for a toddler.
BASE = ("Classic children's storybook illustration for a 4-6 year old, detailed watercolor and ink drawing in the "
        "tradition of Alan Lee and Inga Moore: natural proportions, real expressive faces, realistic landscapes, "
        "atmospheric light, rich but soft colors, no cartoon or chibi look, no text, no letters. Only the "
        "characters mentioned in the scene are shown. Nothing frightening or gory, but the mood may be "
        "adventurous, mysterious or dramatic. ")

# Middle prefix (user decision 2026-09-08, first used for ch. 6): between BASE_OLD (too cute) and BASE (too realistic):
# friendly storybook characters with natural proportions, warm colors, soft light, no chibi, no dark realism.
BASE_MID = ("Classic children's picture-book illustration for a 4-6 year old, warm watercolor and ink in the spirit of "
            "Inga Moore and Pauline Baynes: friendly, expressive, slightly stylized characters with natural proportions "
            "(not chibi, not cartoon, but not photorealistic either), warm rich colors, soft glowing light, real "
            "landscapes with a storybook feel, gentle humor allowed, no text, no letters. Only the characters mentioned "
            "in the scene are shown. Nothing frightening or gory; the mood may be adventurous or mysterious but stays "
            "warm and reassuring. ")
# Which prefix each chapter uses. Chapters not listed use BASE_MID — the confirmed house style (user: "remember
# this style", 2026-09-08). BASE (realistic) is pinned to ch. 4-5 only so their pictures stay reproducible.
BASE_BY_CH = {"04": BASE, "05": BASE}
BASE_DEFAULT = BASE_MID

# Character descriptions, injected ONLY when the scene prompt mentions the keyword (case-insensitive).
CHARS = {
 "bilbo":   "Bilbo is a small curly-haired hobbit with big bare hairy feet, green waistcoat, brass buttons. ",
 "hobbit":  "The hobbit is small and curly-haired with big bare hairy feet, green waistcoat, brass buttons. ",
 "gandalf": "Gandalf is a tall old wizard with a long grey beard, pointed blue hat, grey cloak and a staff. ",
 "dwar":    "Dwarves are short and round, with long beards and colorful hoods. ",
 "thorin":  "Thorin is a proud dwarf with a sky-blue hood with a silver tassel. ",
 "balin":   "Balin is an old dwarf with a white beard and a scarlet hood. ",
 "great goblin": "The Great Goblin is a huge fat goblin with an enormous head and a crooked crown, ugly and loud but not terrifying. ",
 "pony":    "The ponies are small shaggy brown and grey mountain ponies carrying packs. ",
 "ponies":  "The ponies are small shaggy brown and grey mountain ponies carrying packs. ",
 "fili":    "Fili and Kili are the two youngest dwarves, with short yellow beards and blue hoods. ",
 "elrond":  "Elrond is a tall, noble elf-lord with long dark hair, a wise kind face, in a long robe. ",
 "gollum":  "Gollum is a small pale thin creature with big round pale glowing eyes, curious not scary. ",
 "goblin":  "Goblins are small, green-grey, comical and clumsy, not scary. ",
 "spider":  "Giant spiders are round and cartoonish with big eyes, not scary. ",
 "beorn":   "Beorn is a huge man with thick black hair and beard, bare arms, kind stern face. ",
 "elf":     "Elves are slender and graceful, in green and brown, with leaf crowns. ",
 "elves":   "Elves are slender and graceful, in green and brown, with leaf crowns. ",
 "eagle":   "Eagles are huge, golden-brown, noble and kind. ",
 "bombur":  "Bombur is the fattest dwarf, enormously round, with a brown beard and a green hood. ",
 "dori":    "Dori is a dwarf with a purple hood and a grey beard. ",
 "elvenking": "The Elvenking is a tall, stern, golden-haired elf in green and brown with a crown of autumn leaves and berries, on a carved wooden throne. ",
 "wolves":  "Wolves are big and grey, a little silly, not scary. ",
 "warg":    "Wolves are big and grey, a little silly, not scary. ",
 "troll":   "Trolls are big, grey-green, lumpy and silly, not scary. ",
}
def full_prompt(scene, name=""):
    low = scene.lower(); extra = ""
    for k, d in CHARS.items():
        if k in low and d not in extra: extra += d
    base = BASE_BY_CH.get(name.split("_", 1)[0], BASE_DEFAULT)
    return base + extra + scene

SCENES = {
 # --- Chapter 4, re-planned 2026-09-04 against the condensed text (pictures are chosen per text window:
 # the most interesting moment of the window, with exactly the characters/travel mode the text describes).
 "04_climbing_ponies": "Late summer afternoon high in grey mountains: the whole company - thirteen dwarves, Gandalf and Bilbo - ALL riding small shaggy mountain ponies in single file up a steep zigzag path; Bilbo on his pony looks back over his shoulder at green lands far below fading into blue haze; snow on the peaks, a loose boulder bouncing down the slope.",
 "04_storm_giants": "Night thunderstorm in the mountains: dwarves, Gandalf and Bilbo huddle under a rock ledge on a narrow path above a chasm, their ponies standing beside them with heads down and wet tails tucked; Bilbo wrapped in a blanket peeks out; across the valley, lit by a lightning flash, two enormous stone giants toss a boulder to each other and laugh.",
 "04_cave_smoke_rings": "Inside a dry mountain cave at night, storm raging outside the low entrance: dwarves sit wrapped in blankets smoking pipes, the ponies stand together in a corner drying off; Gandalf, seated, blows smoke rings that he turns green, red and blue and sends circling under the cave ceiling; Bilbo watches delighted; the only light is the glowing tip of Gandalf's staff, no fire.",
 "04_orcrist_revealed": "A vast underground goblin hall lit by a big red fire and torches: the Great Goblin on his flat stone seat lets out a furious howl, pointing at an old elvish sword that a goblin guard holds up; before them Thorin and the dwarves stand in a line with hands chained behind their backs and roped together, small Bilbo on his knees at the end of the rope; goblin warriors with axes stamp and gnash their teeth.",
 "04_glamdring_strike": "The same underground hall plunged into darkness: the fire is out, a tall column of blue smoke rises to the ceiling raining white sparks on scattering goblins; in the smoke a sword blade shines with its own cold blue-white light, held by a barely visible tall figure (Gandalf), and the Great Goblin topples from his stone seat; the chained dwarves and Bilbo watch wide-eyed in the foreground.",
 "04_two_swords_corner": "A dark tunnel corner deep inside the mountain: Gandalf and Thorin stand shoulder to shoulder facing a rush of goblins carrying torches; Gandalf's sword Glamdring and Thorin's sword Orcrist blaze with cold blue-white fire lighting their fierce faces; the front goblins drop their torches and fall back in terror; behind Gandalf and Thorin the other dwarves are disappearing round the corner.",
 # --- Chapter 5, re-planned 2026-09-05 against the condensed text (11 windows, best moment per window).
 # Bilbo here: no hood, no cloak (lost to the goblins), green waistcoat with brass buttons still on, small glowing elvish dagger.
 "05_finds_ring": "Pitch-dark goblin tunnel deep under the mountain, the only light a faint cold glimmer: Bilbo, alone, without hood or cloak, on his hands and knees on the rough stone floor, his fingers just touching a small plain gold ring lying in the dust; his face puzzled and frightened, no one else in the picture.",
 "05_gollum_lake": "A vast black underground lake in a cave, ceiling lost in darkness, drops falling from above: Gollum in a tiny crude boat gliding across the still water, paddling with his long bare feet over the sides, his big round pale eyes glowing like two lamps; on the near shore small Bilbo stands frozen, holding out his little elvish dagger that glows faintly blue.",
 "05_riddle_game": "By the black underground lake: Gollum crouches on a wet rock at the water's edge, long fingers on his knees, pale lamp-like eyes fixed on Bilbo; Bilbo sits on a stone opposite him, his faintly glowing dagger across his lap, scratching his curly head as they play the riddle game; only these two, the cave lit by the dagger's faint blue light and Gollum's eyes.",
 "05_fish_jumps": "Funny moment at the underground lake: Gollum, one long bony foot just stepping out of his boat into the water, greedy pale eyes on Bilbo; at that instant a startled silver fish leaps out of the black lake and lands with a splash on Bilbo's big bare hairy foot; Bilbo jumps back in surprise, mouth open, his glowing dagger in hand.",
 "05_pocket_question": "Close, tense scene in the dark cave: Gollum sits on the stone floor right beside Bilbo, uncomfortably close, pale eyes staring; Bilbo, squashed against the cave wall, has one hand deep in his waistcoat pocket, where a tiny golden gleam shows, and looks down puzzled as if asking 'what have I got in my pocket?'; light only from Gollum's eyes and the faint glow of the dagger at Bilbo's belt.",
 "05_three_guesses": "Gollum crouched in the dark, rocking back and forth, holding up three long thin fingers, face screwed up in agonized thinking as he tries to guess; Bilbo stands with his back to the cave wall, small dagger held out in front of him, trying to look brave and calm; only these two, black lake behind.",
 "05_lost_precious": "Gollum on his small rocky island in the middle of the black underground lake, frantically turning over stones and clawing at a crack in the rock, mouth open in a wail of despair, eyes now glowing angry green; his little boat beside the island; far off on the dark shore a tiny figure of Bilbo listening, no one else.",
 "05_gollum_blocks": "A low narrow side tunnel opening in a rough stone wall: Gollum sits hunched right in the opening, blocking it completely, head down between his knees, long arms spread on the floor, green glowing eyes peering into the dark; Bilbo, invisible, is shown only as a faint transparent outline pressed flat against the tunnel wall a few steps away, holding his breath; no other characters.",
 "05_the_leap": "Dramatic action in a low dark tunnel: Bilbo leaps clean over Gollum's head, arms and legs spread, curly hair flying, almost brushing the rock ceiling; below him Gollum twists and grabs upward with long fingers but catches only air, his green eyes wide with fury; the tunnel ahead of Bilbo faintly lighter.",
 "05_stuck_in_door": "A huge stone door standing barely open, dazzling daylight pouring through the gap into a dim guard cave: Bilbo is wedged in the narrow gap, half outside, his green waistcoat's brass buttons caught on the door edge, face straining; inside, a crowd of small green-grey comical goblin guards with swords run about in confusion, bumping into each other, unable to see him; one goblin points at his shadow on the sunlit threshold.",
 "05_buttons_fly": "Bright sunny mountainside outside the goblins' back door: Bilbo tumbles down the stone steps into the sunshine, waistcoat torn open, brass buttons flying through the air in every direction like sparks; behind him on the shadowed porch several comical goblins squint in the sunlight and pick up shiny buttons; green valley and pine trees below.",

 # --- Chapter 6, re-planned 2026-09-05 against the condensed text (11 windows).
 # Bilbo here: NO hood, NO cloak, and his green waistcoat is torn and has LOST all its brass buttons. Nobody has ponies or packs any more.
 "06_balin_watch": "Late afternoon on the eastern mountain slope among boulders and bushes: Balin, an old dwarf with a white beard and scarlet hood, stands on watch between two big rocks, peering straight ahead into the distance; right in front of him, seen from behind and shown as a faint half-transparent outline (invisible), Bilbo creeps up on tiptoe; Bilbo's waistcoat is torn and has no buttons; sunset light, far plains below.",
 "06_burglar_appears": "A sunny hollow among rocks and bushes: Bilbo has just jumped into the middle of the circle of thirteen dwarves and Gandalf, arms spread wide, grinning, his torn waistcoat missing all its buttons, no hood or cloak; the dwarves leap up in astonishment, hoods flying, Balin drops his jaw and pulls off his scarlet hood, Gandalf laughs with delight; nobody has ponies or baggage.",
 "06_scree_slide": "The whole company - Gandalf, thirteen dwarves and small Bilbo - sliding and stumbling down a steep grey scree slope in a cloud of dust, boulders bouncing past them, arms flailing, beards and hoods flying; at the bottom a dark pine wood waiting to catch them; no ponies, no packs; late afternoon light.",
 "06_dwarves_in_trees": "Moonlit forest clearing ringed by tall pines and one larch: thirteen dwarves perched on the branches like startled birds, long beards hanging down, colorful hoods bright in the moonlight - Fili and Kili at the very top of the larch; Gandalf hidden high in a big pine, only his eyes and hat visible; below, Bilbo alone on the ground runs from trunk to trunk in panic; the first grey wolves' eyes glint at the edge of the clearing.",
 "06_dori_lifts_bilbo": "Moonlit clearing under a big pine: Dori, a dwarf with a purple hood and grey beard, stands on the ground with Bilbo climbing onto his shoulders to reach the lowest branch; at the same moment a pack of big grey wolves bursts into the clearing, tongues out, eyes shining; one wolf snaps at the hem of Dori's cloak; other dwarves reach down from the branches above; Bilbo's waistcoat torn and buttonless.",
 "06_fire_cones": "Night, moonlit clearing: Gandalf high in the crown of a pine throws blazing pine cones down into the ring of grey wolves; the cones burn with blue, red and green fire and spit colored sparks; one big wolf, the leader, leaps into the air with a burning cone stuck on his nose; other wolves run in circles with sparks in their fur; dwarves in the surrounding trees cheer.",
 "06_goblin_fire_song": "Night forest clearing full of smoke: a crowd of small green-grey comical goblins with spears dance and sing around the fires they have heaped with ferns and branches at the foot of the pines; up in the branches above the smoke sit the thirteen dwarves and Bilbo, coughing and frightened, beards singed; Gandalf at the top of the tallest pine shakes his staff at the goblins; red firelight from below, moon above.",
 "06_eagle_snatches_gandalf": "Dramatic night scene: the tallest pine is burning, flames licking its lower branches; at its very top Gandalf stands, staff blazing white, about to leap; at that instant the huge golden-brown Lord of the Eagles swoops down from the dark sky, wings spread enormous, and grips Gandalf in his talons; below, astonished goblins and wolves stare up; other eagles diving toward the other trees where dwarves cling.",
 "06_hanging_from_dori": "High in the night sky, far above a dark land with moonlit rivers and cliffs: a huge golden-brown eagle flies with Dori the dwarf (purple hood, grey beard) held in its talons, and Bilbo dangles below Dori, clinging desperately to Dori's ankles with both hands, legs kicking in the air, eyes shut tight; small orange glow of the forest fire far below; other eagles with dwarves in the distance.",
 "06_eagle_lord_talks": "Dawn on a wide rocky shelf high on a mountainside, sky pale pink: the enormous Lord of the Eagles stands on the ledge talking with Gandalf, who leans on his staff, beak close to the wizard's hat; behind them thirteen dwarves sit in a row against the rock wall, tired and dusty; small Bilbo has just been set down on the ledge by another eagle and lies trembling, looking up at the giant bird; no ponies or baggage; no elves, no other people, no other creatures except the eagles.",
 "06_ledge_supper": "Warm evening scene on the mountain ledge: a bright campfire, dwarves roasting rabbits and a lamb on sticks, faces lit orange; two huge golden-brown eagles perched calmly on the rocks nearby watching; Gandalf resting against the rock; Bilbo, fed and content, curled up asleep on the bare stone beside the fire, torn waistcoat without buttons; stars coming out over distant plains.",

 "9_elf_line": "Dwarves blindfolded being led in a line by elves across a bridge over a dark river into a cave-palace.",
 "9_elvenking_hall": "A great hall carved in rock, pillars like tree trunks, the Elvenking on his throne with a crown of berries and leaves.",
 "9_questioning": "The Elvenking questioning stubborn dwarves, elves with spears, dwarves scowling.",
 "9_dwarves_cells": "Dwarves locked in separate stone cells in a corridor lit by torches, an elf guard walking past.",
 "9_bilbo_invisible": "Invisible Bilbo (faint outline) creeping past elf guards in a torchlit corridor.",
 "9_bilbo_finds_thorin": "Bilbo whispering through the keyhole of a cell door, Thorin's surprised eye at the hole.",
 "9_wine_cellar": "Elves rolling big barrels in a stone cellar, a trapdoor over rushing dark water.",
 "9_guards_drink": "Two elf guards and a butler dozing at a table with empty cups, keys on a belt, candle burning.",
 "9_keys": "Bilbo carefully lifting a bunch of keys from a sleeping elf's belt, holding his breath.",
 "9_unlocking": "Bilbo unlocking cell doors one by one, dwarves creeping out into the corridor.",
 "9_into_barrels": "Dwarves climbing into empty barrels, Bilbo packing straw around them, one dwarf's feet sticking out.",
 "9_bombur_barrel": "A fat dwarf squeezed into a barrel, only his nose showing, Bilbo pushing the lid on.",
 "9_trapdoor": "Elves lifting a trapdoor and rolling barrels down into rushing dark water.",
 "9_bilbo_jump": "Bilbo leaping onto the last barrel as it falls through the trapdoor into the water.",
 "9_river_barrels": "Barrels bobbing down a fast forest river, Bilbo clinging to one, wet and cold.",
 "9_raft_elves": "Elves on the riverbank tying barrels together into a raft with poles, lanterns.",
 "9_forest_ends": "The river coming out of the dark forest into open marshland, sky wide, a distant lonely mountain.",
 "9_mountain_view": "A lonely mountain far away across a lake in evening light, Bilbo on a barrel staring at it.",
 "9_laketown_far": "A wooden town on stilts far out on a lake, lights twinkling, evening, barrel raft approaching.",
 "9_bilbo_cold": "Bilbo on a barrel at night shivering and sneezing, wrapped in his coat, stars above.",
 "10_long_lake": "A wide lake with a great mountain rising beyond, the river flowing in, autumn light.",
 "10_laketown": "A wooden town built on stilts over a lake, bridges and boats, wooden houses, smoke from chimneys.",
 "10_barrels_shore": "Barrels pushed onto a shallow shore by elves with poles, a small cabin nearby, dawn.",
 "10_bilbo_opens": "Bilbo prying open a barrel with a knife, a soggy dwarf (Thorin) climbing out stiffly.",
 "10_wet_dwarves": "Thirteen wet, bruised, grumpy dwarves standing on a shore dripping, Bilbo apologetic.",
 "10_bridge_guards": "Thorin and dwarves marching onto a wooden bridge, town guards jumping up in surprise.",
 "10_master_feast": "A great hall in a wooden town, the fat Master at a long table, Thorin announcing himself, elves at the table looking shocked.",
 "10_town_cheers": "Crowds of townspeople cheering on wooden bridges and boats, dwarves waving, lanterns.",
 "10_old_songs": "Townspeople singing old songs about the King under the Mountain, children dancing on the quay.",
 "10_dwarves_fine": "Dwarves in fine new clothes with combed beards, looking very important in a town street.",
 "10_bilbo_cold_town": "Bilbo with a red nose and a blanket, sneezing, in a warm wooden room, tea nearby.",
 "10_boats_loaded": "Big boats being loaded with supplies and ponies on a lake shore, dwarves supervising.",
 "10_departure": "Boats rowing away up the lake toward the mountain, townspeople waving from the quay, autumn.",
 "10_mountain_ahead": "A boat on a grey lake, the lonely mountain looming ahead under cloudy sky, Bilbo looking worried.",

 "01_hall": "Inside a cozy hobbit hole: round tunnel hallway with panelled walls, pegs with coats, many round doors, warm light.",
 "01_bilbo_father": "A respectable old hobbit couple in old-fashioned clothes standing in front of a fine hobbit hole, portrait style.",
 "01_gandalf_fireworks": "Colorful fireworks shaped like flowers and dragons over a hobbit village at night, children cheering.",
 "01_scratch_door": "Gandalf scratching a secret rune mark on a round green door with the tip of his staff, evening light.",
 "01_cakes": "A hobbit pantry stuffed with cakes, pies, cheeses, and jars, Bilbo carrying a tray, two dwarves waiting eagerly.",
 "01_pipes": "Dwarves and Gandalf smoking pipes in a hobbit parlour, smoke rings floating up and around the room, evening.",
 "01_fireplace_talk": "Thorin and Gandalf talking seriously by the fireplace, Bilbo peeking from behind a doorway holding a candle.",
 "01_lonely_mountain": "A lonely tall mountain far away over a lake and a ruined town, a great red dragon sleeping on gold inside, dreamlike.",
 "01_bilbo_burglar": "Bilbo standing bravely with hands on hips declaring himself a burglar, dwarves surprised, cozy room.",
 "02_note": "A note left on the mantelpiece of a hobbit parlour, morning sunlight, Bilbo reading it with an alarmed face.",
 "02_green_hills": "A small company on ponies passing green hills, hedges and a little village with a stone bridge, spring day.",
 "02_wet_camp": "Dwarves trying to light a fire under dripping trees, rain, a pony slipping in a river, baggage floating away.",
 "02_bilbo_purse": "Bilbo holding a fat leather purse with a grumpy face on it, in the moonlight near a troll's back.",
 "02_trolls_fight": "Three big trolls wrestling and hitting each other in a heap by a fire, dwarves hiding in bushes, night.",
 "02_dawn": "Sunrise light breaking through trees onto a forest clearing, a bird singing, first golden rays.",
 "02_gold_pots": "Gandalf and dwarves burying pots of gold coins under a big tree by a river, whispering spells, Bilbo watching.",
 "03_far_mountains": "A wide moor with heather and bogs, misty mountains rising far away, small travelers on ponies, cloudy sky.",
 "03_valley_path": "A steep winding path down into a hidden green valley, pine trees, a river far below, evening glow.",
 "03_elf_talk": "Bilbo talking with a laughing elf on a stone bridge over a rushing stream, lanterns hanging in the trees.",
 "03_leaving_rivendell": "Travelers on ponies leaving a beautiful elven valley in the morning, elves waving from the trees, mountains ahead.",

 "01_hobbit_feet": "A close-up of a cheerful hobbit with curly hair and big hairy feet, standing in a flower garden, waving.",
 "01_dwalin": "A single dwarf with a blue hood and long beard bowing politely at a round green door, Bilbo peeking out.",
 "01_more_dwarves": "Several dwarves with red, yellow and green hoods tumbling through a round door in a heap, Bilbo dismayed.",
 "01_thorin": "A proud dwarf king Thorin with a sky-blue hood, silver tassel and long beard, standing importantly in a hobbit hallway.",
 "01_washing_up": "Dwarves tossing plates and cups to each other in a hobbit kitchen, juggling dishes, singing, Bilbo worried.",
 "01_dragon_song": "Dwarves singing around a fireplace, smoke shaping a great red dragon curled on gold, Bilbo listening wide-eyed.",
 "01_bilbo_scared": "Bilbo the hobbit fainted on a rug, dwarves and Gandalf leaning over him with concern, cozy candlelit room.",
 "01_bilbo_bed": "Bilbo asleep in a small round bed under a quilt, moonlight through a round window, dreams of mountains.",
 "02_messy_kitchen": "A hobbit kitchen after breakfast, piles of dirty dishes, Bilbo in a dressing gown holding a note, morning.",
 "02_inn": "Dwarves and a hobbit at a cozy village inn, Gandalf arriving, ponies outside, a green dragon sign.",
 "02_fire_light": "A tiny light glowing between dark trees at night, dwarves peering from bushes, a hobbit sent forward.",
 "02_troll_pocket": "A troll holding a tiny hobbit up by the collar, two other trolls staring, a talking purse falling out of a pocket.",
 "02_dwarves_sacks": "Dwarves tied up in sacks lying around a campfire, trolls arguing about how to cook them, Bilbo hiding up a tree.",
 "02_gandalf_voice": "Gandalf hiding behind a big tree in the dark, whispering, trolls looking around confused, first light of dawn on the horizon.",
 "02_troll_cave": "A dark stone cave full of pots, old clothes, bones, and a glint of gold and swords, Gandalf holding a torch.",
 "02_swords": "Gandalf and Thorin holding two beautiful old elvish swords, Bilbo holding a small dagger, in a forest clearing.",
 "03_river_ford": "A company on ponies fording a wide shallow river among rocks and heather, distant misty mountains.",
 "03_elves_singing": "Playful elves in green sitting in trees by a river, laughing and singing at travelers on ponies, lantern light in dusk.",
 "03_last_homely_house": "A warm elven house with many lights in the evening, travelers being welcomed at a door, waterfall nearby.",
 "03_midsummer_eve": "Elves and dwarves feasting outdoors under lanterns in trees on a midsummer night, starry sky, Bilbo happy.",
 "01_bagend": "A round green door of a cozy hobbit hole set into a sunny hillside, flowers, a little path, morning light.",
 "01_bilbo_pipe": "Bilbo the hobbit sitting on a bench by his round door, blowing smoke rings from a long pipe, content.",
 "01_gandalf_arrives": "Tall wizard Gandalf with pointed hat standing at the garden gate talking to a surprised little hobbit Bilbo.",
 "01_dwarves_door": "A crowd of thirteen cheerful dwarves with colorful hoods and long beards crammed at a round hobbit door.",
 "01_tea_party": "A cozy hobbit kitchen full of dwarves eating cakes, drinking tea, one dwarf playing a harp, Bilbo looking flustered.",
 "01_map": "Gandalf and dwarves around a table looking at an old parchment map by candlelight, a dragon drawn on the map.",
 "02_leaving": "Bilbo running out of his hobbit hole without a hat, waving, in a hurry, sunny morning, green hills.",
 "02_ponies": "A company of dwarves and a hobbit riding ponies along a country road, Gandalf on a white horse, rolling hills.",
 "02_rain": "Dwarves and a hobbit riding ponies in the rain under dark trees, looking miserable, a small light in the distance.",
 "02_trolls": "Three big silly trolls sitting around a campfire in the woods at night, roasting mutton, grumbling.",
 "02_bilbo_sneak": "Tiny Bilbo the hobbit sneaking behind a tree toward a troll's pocket, big eyes, moonlight.",
 "02_stone_trolls": "Three trolls turned to grey stone in a forest clearing at dawn, sunlight, birds, dwarves peeking out.",
 "03_rivendell": "A beautiful elven valley with waterfalls, graceful bridges and a fair house among trees, golden evening light.",
 "03_elrond": "A wise, kind elf lord with long dark hair examining a glowing sword, Gandalf and Bilbo watching.",
 "03_moon_letters": "Gandalf, Bilbo and a dwarf looking at an old map held up to the moonlight, silver runes glowing on it.",
 "03_mountains": "A small company of travelers on a narrow mountain path, huge snowy peaks, storm clouds, stone giants far away throwing rocks.",
 # --- Chapter 7 (Beorn), re-planned 2026-09-07 against the condensed text: 11 windows, best moment per window.
 # Travel mode: ON FOOT from the Carrock to Beorn's house (no ponies - lost to the goblins); ON PONIES from Beorn's house to Mirkwood, Gandalf on a horse.
 "07_eagle_ride": "Dawn high above misty valleys: fifteen huge golden-brown eagles flying in a long line, each carrying a passenger; in front, small Bilbo lies flat on an eagle's back with eyes squeezed shut, clutching the feathers with both hands; on the other eagles dwarves in colorful hoods and Gandalf with his pointed hat cling on; grey mountains falling away behind, sun just rising over a forest far to the east.",
 "07_bee_meadow": "Hot summer afternoon on a rolling meadow of purple and white clover humming with bees: Gandalf, Bilbo and thirteen dwarves walk ON FOOT in a straggling line through the tall flowers (no ponies, no packs); in the foreground a bee bigger than a hornet with gleaming golden stripes hovers right in front of Bilbo's nose and he leans back warily; distant oak groves ahead.",
 "07_beorn_axe": "Sunlit farmyard inside a wooden fence: the trunk of a giant oak lies on the ground, and beside it stands Beorn, a man of gigantic height with thick black hair and beard, bare muscular arms, in a knee-length woollen tunic, leaning on a huge axe and scowling down; two sleek horses nuzzle his shoulders; before him tall Gandalf in grey with his staff and, barely reaching Beorn's knee, tiny Bilbo bowing nervously, his green waistcoat missing several brass buttons.",
 "07_dwarves_by_twos": "Beorn's sunny wooden veranda with a flower garden below: Beorn sits on a bench, arms crossed, trying not to laugh; Gandalf beside him mid-story; Bilbo sits on a low bench swinging his legs; on the garden path two dwarves, Balin with a white beard and scarlet hood and Dwalin with a dark-blue hood, bow so low that their beards sweep the gravel; on the veranda steps four dwarves who already arrived (Thorin in a sky-blue hood, Dori, Nori, Ori) sit meekly in a row.",
 "07_bombur_last": "Beorn's veranda now crowded: Gandalf, Bilbo and twelve dwarves in colorful hoods squeezed on benches and steps; up the garden path runs Bombur, the fattest dwarf, red-faced and puffing, hood askew, arriving last; huge Beorn stands with a hand raised counting on his fingers, exasperated but amused; late afternoon light, bees among the flowers.",
 "07_animal_servants": "Inside Beorn's great wooden hall at night, a fire burning in the middle and tree-trunk pillars: big grey dogs walking on their hind legs carry blazing torches and set them in brackets, snow-white sheep carry trays with dishes on their broad backs, and white ponies roll round log stools toward the low tables; Bilbo watches open-mouthed from the doorway with Gandalf and a few dwarves behind him; warm firelight, smoke rising to a hole in the roof.",
 "07_night_growl": "Deep night inside Beorn's dark hall: dwarves and Gandalf asleep in a row under blankets on a raised platform between pillars; Bilbo sits up in his blankets wide awake, eyes big, listening; a patch of moonlight lies on the floor from the smoke-hole; through the crack of the great door and a window shutter, huge shadowy bear shapes and one glinting eye can be sensed outside; only embers glow in the hearth; mysterious but not frightening.",
 "07_beorn_warning": "Morning on Beorn's veranda over a breakfast of honey, bread and cream: enormous Beorn leans forward across the low table, one big finger raised in warning, face serious; Gandalf, Bilbo and the thirteen dwarves listen intently; on the table a clay honey pot and stacks of flat honey cakes; beyond the garden fence, far away on the eastern horizon, a dark line of forest.",
 "07_riding_bear_follows": "Dusk on wide grassland with mountains dark on the left and a red sunset behind: the whole company gallops in a line on Beorn's shaggy ponies - thirteen dwarves and Bilbo each on a pony, Gandalf ahead on a tall horse; in the grass off to one side, half-hidden in the shadows, the huge dark shape of a great bear runs along keeping pace with them; Bilbo on his pony looks over at it uneasily.",
 "07_ponies_home": "Noon at the edge of Mirkwood, a wall of huge gnarled dark trees hung with ivy: the riderless ponies trot happily away across the grass with their tails toward the forest; the dwarves and Bilbo stand ON FOOT with heavy packs and water-skins on their backs watching them go; Gandalf still sits on his tall horse; deep in the tree shadows at the forest edge a huge bear shape slips after the ponies.",
 "07_gandalf_farewell": "The forest edge: Gandalf, already far off on his galloping horse, twists in the saddle with both hands cupped around his mouth, shouting back; in the foreground thirteen dwarves with packs and Bilbo with his own too-big pack stand at a dark arch formed by two ancient ivy-covered trees, the black tunnel of the forest path behind them; Bilbo looks back sadly at the wizard; bright open grassland behind Gandalf, gloom under the trees.",
 # --- Chapter 8 (Mirkwood, spiders), re-planned 2026-09-07 against the condensed text: 12 windows.
 # Bilbo: no hood or cloak, green waistcoat, small glowing elvish dagger (named Sting in this chapter). The company is ON FOOT with packs; Gandalf is NOT present in this chapter.
 "08_eyes_in_dark": "Pitch-black night camp on the narrow forest path in Mirkwood: thirteen dwarves and Bilbo huddled close together in a heap under blankets, no fire; all around them in the darkness dozens of pairs of glowing eyes - yellow, red, green and pale bulging insect eyes - stare from between the tree trunks and from the branches above; Bilbo, on watch, sits up clutching his knees and stares back; the only light comes from the eyes.",
 "08_deer_leap": "Dramatic moment at a black fast river crossing the forest path in gloomy green twilight: a great dark deer with antlers sails through the air in a mighty leap over the water; below it the fat dwarf Bombur, knocked off balance, topples backwards off the bank into the black water with arms flailing, the small boat drifting away; Thorin on the far bank stands calm with a bow drawn; other dwarves sprawled on the ground where the deer knocked them down; Bilbo shouts pointing at Bombur.",
 "08_butterflies": "Bright sunshine above the forest canopy: Bilbo's head and shoulders poke up out of a sea of dense green leaves stretching to the horizon in every direction, rippling in the wind; he clings to the thin top branches of a giant oak, face turned up to the sun and breeze, eyes half closed with delight; hundreds of velvet-black butterflies flutter around his curly head; blue sky, no other characters.",
 "08_elf_feast": "Night in the forest: a clearing lit by a big fire and torches on the trees, where wood-elves in green and brown with leaf crowns sit on log stools feasting, laughing and drinking; in the dark foreground, peering out between tree trunks, the hungry faces of Bilbo and the dwarves - Thorin, Balin, Bombur and others - eyes wide, Bombur licking his lips; the warm firelight on their faces against the surrounding blackness.",
 "08_elvenking_feast": "A grand elvish feast under the trees at night, hundreds of torches and lanterns, elves playing harps and singing, flowers in their shining hair, green and white gems on their belts; at the head of the long feast sits the Elvenking, golden-haired, with a crown of leaves; into the middle of the circle of light steps Thorin in his sky-blue hood, hand raised, gaunt and hungry; behind him in the shadows the other dwarves and Bilbo; the elves turn toward him in surprise, the instant before every light goes out.",
 "08_bilbo_vs_spider": "Dim green forest gloom: Bilbo, still half wrapped in thick grey spider silk around his legs, stands over a giant spider as big as himself, striking at its cluster of eyes with his small elvish dagger that glows pale blue; the spider rears back on its hairy legs, startled; sticky threads hang from the branches all around; Bilbo's face fierce and determined; dramatic but not gory, no blood.",
 "08_cocoons": "A dark part of the forest thick with black webs: a high branch from which a dozen grey silk cocoons hang in a row like huge bundles, with a dwarf's boot, a nose tip, a bit of beard or the corner of a colorful hood poking out of each; a fat spider on the branch pinches the nose sticking out of the biggest cocoon (Bombur), and a foot bursts out and kicks it; other giant spiders sit around on the webs; far below on the forest floor Bilbo, invisible, is only a faint transparent outline peering up in horror.",
 "08_stones_and_song": "Forest floor among huge tree trunks and webs: Bilbo, shown as a faint half-transparent ghostly outline because he wears the ring, is caught mid-throw hurling an egg-sized stone, mouth open in song; one giant spider tumbles head over heels off a branch, another crashes through a torn web; a crowd of furious spiders rushes toward the wrong tree, their many eyes glaring; a dry stream bed full of pebbles at Bilbo's feet.",
 "08_battle_under_tree": "Under the cocoon tree in the gloom: twelve exhausted dwarves in tattered hoods, still trailing bits of grey silk, stand back to back with sticks, knives and stones - Bombur held upright between his brother Bofur and cousin Bifur; small Bilbo leaps in front of them slashing at spiders with his glowing dagger, cutting strands of web; a ring of hundreds of giant spiders on the ground and on the branches around them; frantic but not gory.",
 "08_bilbo_vanishes": "In the middle of the spider-ringed dwarves: Bilbo, holding up his hand with a small gold ring, is half faded into transparency, in the very act of disappearing; the dwarves nearest him - Balin with white beard and scarlet hood, Fili and Kili in blue hoods - stare with mouths open and eyes popping in astonishment; spiders spinning webs from tree to tree behind them; gloomy forest light.",
 "08_thorin_before_king": "A great cavern hall lit by lanterns, its pillars carved like tree trunks, an underground river glinting through the gate: the Elvenking sits on a carved wooden throne with a crown of autumn leaves and berries, golden-haired, stern, holding a carved oak staff; before him stands Thorin, hands bound with rope, hood torn, lips pressed shut in stubborn silence; tall elf guards with spears and long bows on either side.",
 "08_thorin_cell": "A small stone cell deep in the Elvenking's caves with a heavy oak door and a tiny barred window: Thorin sits on a straw bed, his sky-blue hood pulled down, chin on his fist, brooding; beside him on the floor a loaf of bread, a piece of cheese and a jug of water, untouched; the light of a single lantern; quiet, thoughtful mood.",
}

def gen(name, prompt):
    ch, slug = name.split("_", 1)
    out = pathlib.Path("img") / f"chapter-{int(ch)}" / f"{slug}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        return name, "skip"
    if BACKEND == "openai":
        body = json.dumps({"model": "gpt-image-1", "prompt": full_prompt(prompt, name),
                           "size": "1536x1024", "quality": "medium", "n": 1}).encode()
        req = urllib.request.Request("https://api.openai.com/v1/images/generations", data=body,
            headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"})
    else:
        body = json.dumps({"model": OR_MODEL, "modalities": ["image", "text"],
                           "image_config": {"aspect_ratio": "3:2", "image_size": "1536x1024", "quality": "medium"},
                           "messages": [{"role": "user", "content": "Generate one illustration. " + full_prompt(prompt, name)}]}).encode()
        req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", data=body,
            headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json",
                     "HTTP-Referer": "https://github.com/askolesov", "X-Title": "hobbit-reader"})
    import time
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                data = json.load(r)
            if BACKEND == "openai":
                b64 = data["data"][0]["b64_json"]
            else:
                imgs = data["choices"][0]["message"].get("images") or []
                if not imgs:
                    return name, "ERR no image in response: " + json.dumps(data)[:300]
                url = imgs[0]["image_url"]["url"]
                b64 = url.split(",", 1)[1] if url.startswith("data:") else base64.b64encode(urllib.request.urlopen(url).read()).decode()
            out.write_bytes(base64.b64decode(b64))
            return name, "ok"
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 5:
                time.sleep(20 * (attempt + 1)); continue
            return name, f"ERR {e} {e.read()[:300]!r}"
        except Exception as e:
            return name, f"ERR {e}"

# run from the package dir: images go to ./img/chapter-N/
with concurrent.futures.ThreadPoolExecutor(4) as ex:
    todo = [(k, v) for k, v in SCENES.items() if not ONLY or k in ONLY]
    for name, st in ex.map(lambda kv: gen(*kv), todo):
        print(name, st, flush=True)
