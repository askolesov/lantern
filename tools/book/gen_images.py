#!/usr/bin/env python3
"""Generate storybook illustrations for chapters of The Hobbit via OpenAI gpt-image-1.
Usage: OPENAI_API_KEY=... python3 gen_images.py
"""
import base64, json, os, re, sys, urllib.request, concurrent.futures, pathlib

# Backends: OPENAI_API_KEY -> api.openai.com gpt-image-1 (original); otherwise OPENROUTER_API_KEY ->
# openrouter.ai chat completions with an image-output model (added 2026-09-04; key lives in
# life/dossiers/2026-08-local-ai-hardware/.env, source it before running — never copy it into this repo).
KEY = os.environ.get("OPENAI_API_KEY"); BACKEND = "openai"
if not KEY:
    KEY = os.environ.get("OPENROUTER_API_KEY"); BACKEND = "openrouter"
if not KEY:
    sys.exit("OPENAI_API_KEY or OPENROUTER_API_KEY not set")
OR_MODEL = os.environ.get("OR_MODEL", "openai/gpt-5-image")
ARGS = sys.argv[1:]
DRY  = "--dry-run" in ARGS            # print prompts + matched CHARS keys, call no API, spend nothing
ALL  = "--all" in ARGS
ONLY = [a for a in ARGS if not a.startswith("--")]   # scene names, e.g. `python3 gen_images.py 04_climbing_ponies`
if not ONLY and not ALL:
    sys.exit("refusing to run with no scene names: that would generate every missing scene in SCENES,\n"
             "including any stale draft entries, and spend real money (~$0.065/picture).\n"
             "Pass explicit names, or --all to really mean all. Add --dry-run to preview prompts for free.")

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
 "smaug":   "Smaug is a huge, magnificent red-and-gold dragon with long folded bat-like wings, a sinuous armored body glittering with gold and jewels grown into his pale belly scales, and glowing eyes; impressive and proud, not gory or grotesque. ",
 "dragon":  "The dragon is huge and magnificent, red-and-gold, with long folded bat-like wings, a sinuous armored body glittering with gold and jewels grown into his pale belly scales, and glowing eyes; impressive and proud, not gory or grotesque. ",
 "bard":    "Bard is a tall, grim, dark-haired bowman of Lake-town in plain grey and brown clothes, carrying a great black bow. ",
 "dain":    "Dain is a stout, battle-worn dwarf lord in iron mail and a red hood, at the head of armored dwarves from the Iron Hills. ",
 "master":  "The Master of Lake-town is a portly, self-important man in a fur-trimmed velvet robe and a gold chain of office. ",
 "roac":    "Roac is a very old, wise raven with grey-flecked feathers, a dignified messenger, not sinister. ",
}
def full_prompt(scene, name="", trace=None):
    # Match at a WORD START only. Plain `k in low` matched substrings, so "himself"/"itself" pulled in
    # the "elf" description and silently put elves in the frame (lesson 2026-09-12). "\bdwar" still
    # catches "dwarves"/"dwarf"; "\belf" catches "elf"/"elves" but not "himself".
    low = scene.lower(); extra = ""
    for k, d in CHARS.items():
        if re.search(r"\b" + re.escape(k), low) and d not in extra:
            extra += d
            if trace is not None: trace.append(k)
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

 # --- Chapter 10, re-planned 2026-09-16 against the condensed text (11 windows, best moment per window;
 # the old 14-slot draft list above was written against the pre-condense full text and is stale, moved to
 # img-old reasoning in CLAUDE.md notes). Thorin here: torn, soaked, filthy sky-blue hood with a tarnished
 # silver tassel, a gold chain at his throat, NO weapons (elves took the knives and Orcrist). No ponies in
 # this chapter (sent overland separately, off-page).
 "10_mountain_sighted": "Dawn on a wide river bending around a tall cliff, forest falling away behind: a line of wooden barrels bobs down the current, and on the nearest one Bilbo lies sprawled clinging to the rim, curly hair dripping, lifting his head to look out across a wide marshy plain where the river splits into many channels; far off through ragged clouds looms the dark peak of the Lonely Mountain, alone above the mist; Bilbo's face shows dismay, not joy; no other figures visible.",
 "10_long_lake": "Sunset over a vast lake so wide the far shore is lost in haze: a swift river pours in between two weathered stone towers rising from shingle at the river mouth, water sheeted with the last orange light; a raft of barrels glides through the gap into the open water, tiny in the great expanse; the dark shape of the Lonely Mountain barely visible far to the north; wide landscape view, no close figures.",
 "10_laketown": "Blue dusk over the lake: a large wooden town built entirely on tall pilings out over the water, plank streets and houses with lit windows and rising chimney smoke, joined to the shore by one great wooden bridge; boats move between the buildings; torches just being lit along the quay; the dark line of the forest behind; a hushed, golden-lit town, no figures prominent.",
 "10_bilbo_frees_thorin": "Full night on a dark riverbank, round barrels beached in mud and shallow water: Bilbo wrenches the lid off one barrel with a knife, wet straw spilling out; from inside, Thorin claws his way upright, soaked to the skin, filthy and dishevelled, his sky-blue hood dark with water and its silver tassel tarnished, a gold chain glinting at his throat; Thorin's face is pained and stiff as he groans to his feet; no other dwarves visible yet, only faint starlight.",
 "10_dwarves_ashore": "Night on a muddy riverbank strewn with open barrels and scattered straw: a dozen dwarves lie and sit sprawled in exhaustion, soaked and bruised, none carrying any weapon or pack; Fili and Kili, the two youngest with short yellow beards and blue hoods, crouch helping an older dwarf sit up; in the middle, fat Bombur with his brown beard and green hood lies utterly still, eyes shut, a faint smile on his face; Bilbo moves among them, checking each one, worried.",
 "10_thorin_at_the_hut": "Torchlit night at a small guard hut beside a great wooden bridge: Thorin stands square in the open doorway, ragged and dripping but head high, gold chain and tarnished sky-blue hood catching the light, empty hands spread open to show he carries no weapon; behind him Fili, Kili and small Bilbo crowd close, equally unarmed and bedraggled; inside the hut, startled town guards in leather jerkins scramble up from a table, snatching spears, faces wide with shock.",
 "10_thorin_in_the_hall": "A long wooden feast-hall lit by hanging lamps and a roaring hearth, townsfolk seated at long tables loaded with food and drink: every head turns as Thorin strides in through the open doors, ragged cloak and gold chain, chin lifted, one hand raised; Fili, Kili and Bilbo follow just behind him; men half rise from the benches, cups stopped halfway, astonished faces on every side; a few wood-elves at a side table stare in open-mouthed disbelief.",
 "10_town_sings": "Night over the lake town, warm light spilling from every window and doorway onto the wooden quays: crowds of townsfolk in cloaks and shawls stand pressed along the rails and balconies, torches held high, mouths open in song; the black water below throws back a hundred small reflected flames; no single figure prominent, a whole town singing together.",
 "10_thorin_enthroned": "Inside the Master's great feast-hall, warmly lit: Thorin sits upright in a huge carved wooden chair on a low dais, gold chain gleaming against his sky-blue hood, looking every inch a king despite his travel-worn cloak; Fili and Kili stand proudly on either side of the chair; at a smaller table just below, small Bilbo eats happily among plates of food, a little overwhelmed; townsfolk crowd the hall behind them, raising cups, a harpist playing in the corner.",
 "10_bilbo_sick": "A small warm wooden room lit by a low fire: Bilbo sits wrapped to the chin in a thick blanket in a big chair pulled close to the hearth, curly hair damp, nose red, eyes half-shut and miserable, a steaming cup on a stool beside him; through the shuttered window a faint golden glow and the muffled sound of singing and harps drifts in from the feast outside; nobody else in the room.",
 "10_departure": "A grey blustery autumn morning on the lake: three long wooden boats pull away from broad steps leading up to the town, oars dipping together, dwarves and Bilbo seated among sacks and barrels of supplies; townsfolk crowd the steps and windows above, waving and calling; ahead across the water, under low cloud, the dark bulk of the Lonely Mountain rises directly in their path; Bilbo, wrapped in a cloak, looks toward it without joy while the dwarves cheer.",

 # --- Chapter 11, planned 2026-09-16 against the condensed text (9 windows, best moment per window).
 "11_company_departs": "A grey riverbank at dusk: laden ponies and a couple of packhorses stand ready, dwarves loading sacks and tools, small Bilbo among them; a few Lake-town men hurry away back along the shore, glancing nervously over their shoulders; across the water the dark bulk of the Lonely Mountain looms under a heavy sky, closer and more threatening than before.",
 "11_desolation_march": "A bleak grey plain of cracked earth and blackened tree stumps stretching toward the Lonely Mountain: Thorin's company - dwarves leading heavy-laden ponies, Bilbo and Balin riding at the back - trudge in a silent straggling line, heads down, no laughter, no song; the Mountain fills the sky ahead, dark and cold.",
 "11_scouting_gate": "Crouched behind grey boulders on a rocky spur: Balin (white beard, scarlet hood), Fili, Kili and small Bilbo peer down across a rushing river at the grey ruins of the ancient town of Dale in the valley below, and beyond it a huge dark tunnel mouth in a sheer cliff wall, steam and black smoke curling out of it; one black raven wheels overhead.",
 "11_map_by_firelight": "Evening at a small campfire in a narrow valley below the Mountain's western spurs: Bilbo sits cross-legged studying Thorin's old map by the firelight, tracing the moon-runes with one finger, brow furrowed in concentration; Thorin, Balin and a couple of other dwarves lean in around him, watching; ponies grazing in the shadows behind.",
 "11_finding_the_door": "A narrow grassy ledge high on the Mountain's western slope, sheltered between rock walls, empty sky beyond: Fili, Kili and Bilbo stand before a smooth, flat, featureless stretch of cliff wall, tracing their hands over the bare stone in excitement, no doorframe or keyhole visible - only the two dwarves and the hobbit, no one else on the ledge.",
 "11_hauling_up_ropes": "A dizzying narrow ledge above a sheer drop, ropes tied around the dwarves' waists trailing up the cliff: several dwarves haul packs and tools up hand over hand toward the grassy shelf above; far below on the valley floor, fat Bombur (brown beard, green hood) stands stubbornly beside the ponies, arms crossed, refusing to climb.",
 "11_bilbo_on_the_doorstep": "The small grassy shelf below the smooth cliff wall, sheltered and quiet: Bilbo sits alone with his back against the rock, knees drawn up, gazing west over the valley toward the dark line of Mirkwood and, faint on the horizon, the tiny peaks of the Misty Mountains; a big grey snail crawls in the grass beside him; no dwarves in view, wistful mood, late afternoon light.",
 "11_dwarves_grumble": "Above the grassy shelf, a handful of dwarves - Thorin, Bifur, Dwalin - sit talking on the rocks, gesturing down toward the distant Front Gate; below and out of their sight, small Bilbo sits against the cliff wall with his back to them, overhearing, his face troubled and a little hurt.",
 "11_thrush_and_door": "Sunset on the little grassy shelf: a large black thrush with a pale speckled breast perched on the grey stone, cracking a snail shell with sharp taps; a single red ray of sunlight breaks through heavy clouds and strikes the smooth cliff wall, and at that exact spot the stone is splitting open, a crack of deep shadow appearing at the height of a door; Bilbo and several dwarves rush toward it across the grass, Thorin in front reaching for a key on a chain around his neck.",

 # --- Chapter 12, planned 2026-09-16 against the condensed text (15 windows, best moment per window; this is
 # the longest and most important chapter - the Smaug conversation - so it gets more slots than usual).
 # Smaug: huge red-and-gold dragon, folded bat-like wings, jeweled armored belly; impressive, not gory or scary.
 "12_thorin_sends_bilbo": "Night on the little grassy shelf before the open black doorway in the cliff, stars overhead: the company of dwarves stands in a loose half-circle, Thorin gesturing toward the dark opening with one hand; small Bilbo steps forward alone, hand resting on his sword hilt, chin lifted; old Balin stands closest to him, about to follow him partway in.",
 "12_bilbo_descends": "A long straight stone tunnel cut smooth by ancient dwarf-masons, sloping gently down into total darkness: alone, Bilbo walks forward with one hand trailing the wall and the other on his small sword hilt, a faint transparent outline because he wears the ring; far behind him a last speck of starlit doorway is barely visible.",
 "12_tunnel_glow": "The tunnel's far end, a round opening the same size as the door above: Bilbo's small silhouette crouches at the threshold, peering through into deep blackness where a dull red glow is just beginning to color the edges of the opening; wisps of hot vapor drift past him; his face is a mix of dread and determination.",
 "12_smaug_hoard": "A vast underground hall lost in shadow, its floor blazing with light: Smaug, an immense red-and-gold dragon, lies fast asleep on top of an unimaginable mountain of treasure - heaped gold coins, armor, jeweled cups and weapons - his folded bat-like wings and long tail draped over the glittering hoard, his pale belly armored with embedded gems; tiny Bilbo's head and shoulders peek from a dark tunnel opening at the edge of the hall, awestruck.",
 "12_bilbo_steals_cup": "Close to the foot of the golden hoard in the red firelight: small transparent-outlined Bilbo (wearing the ring) reaches up with both hands to lift a huge two-handled golden cup from a pile of treasure, straining under its weight; just above him, unimaginably huge, one of Smaug's wings twitches and his sleeping face shifts, a slit of eye almost showing - a heart-stopping moment.",
 "12_smaug_bursts_out": "Night sky above the Mountain's Front Gate, seen from a distance: Smaug bursts up out of the dark tunnel mouth in a colossal spray of steam, wreathed in green and red fire, wings spread wide as he climbs roaring into the sky above the peak; below, tiny dwarf figures press flat against the terrace wall, hiding under an overhang of rock.",
 "12_rope_rescue": "The narrow ledge above the valley, ropes taut: dwarves haul fat Bofur and then rounder Bombur up over the cliff edge on ropes around their waists, everyone straining and hurrying; behind them, low over the mountainside, a streak of orange dragon-fire lights the night sky as Smaug wheels past hunting; packs and tools dangle on ropes still being pulled up.",
 "12_second_descent_eye": "The end of the tunnel by day, dim red light beyond: Bilbo, a faint transparent outline from the ring, freezes just short of the opening - through the crack he can see, under Smaug's massive lowered eyelid, one thin line of fierce red eye watching, unmoving; the dragon is only pretending to sleep.",
 "12_riddle_names": "Deep inside the vast treasure hall, dramatic red firelight: Smaug's enormous head is raised and turned toward the tunnel opening, listening with amusement; before him on the gold, small Bilbo (a faint transparent outline from the ring) stands with one hand raised, mid-speech, clearly in the middle of reciting his fantastical riddling names; the dragon's huge eye is fixed on him, glowing.",
 "12_barrel_rider_taunt": "Close on Smaug's huge head looming over the gold, jaws curled in a sly, mocking almost-smile, one eye half-closed cunningly; small transparent-outlined Bilbo stands his ground below, arms crossed defensively, trying to look unbothered; scattered gold coins and a few old bones visible near the dragon's claws.",
 "12_smaug_revenge_roar": "Smaug rears up to his full height over the treasure hoard, wings half-spread, throat glowing from within, eyes blazing red light that floods the whole cavern from floor to ceiling in a dramatic wash of crimson; small transparent-outlined Bilbo cowers low against a heap of gold in the foreground, overwhelmed by the dragon's fury and pride.",
 "12_diamond_waistcoat": "Smaug rolls partly onto his side in the golden firelight, proudly displaying his long pale belly armored edge to edge with embedded gold and gems like a coat of mail; small transparent-outlined Bilbo stands looking up at it appraisingly, one hand almost to his chin, studying the dragon's underside intently.",
 "12_bilbo_burnt_escape": "The tunnel seen from inside, mid-escape: small Bilbo sprints up the sloping passage away from the camera, arms pumping, hair and the back of his waistcoat smoking; behind him the tunnel mouth glows white-hot as a jet of dragon fire and steam roars up the passage just short of catching him, throwing his fleeing silhouette into sharp orange light.",
 "12_thrush_listens": "Dusk on the little grassy shelf: Bilbo lies slumped against the cliff wall, soot-streaked, singed hair, eyes closed with exhaustion, while Balin and another dwarf tend to him with a water skin and cloth; a few steps away the same big black thrush sits very still on its grey stone, head cocked, listening intently to their low voices.",
 "12_smaug_flies_to_lake": "Night sky over the wide dark valley: Smaug flies south high above the winding river, wings beating slow and powerful, his whole long body glowing and glittering like a great flying torch against the black clouds and stars; far below, the Mountain falls away behind him, tiny points of firelight from a distant lake town just visible ahead on the horizon.",

 # --- Chapter 13, planned 2026-09-16 against the condensed text; STUBS ONLY (placeholder art, no AI generation yet). ---
 "13_door_blocked": 'Deep underground tunnel, pitch dark except a few glints of firelight: Thorin and dwarves crowd around a pile of fallen rock that fills the tunnel from floor to ceiling, hands pressed to the stone in despair; Bilbo stands slightly apart, small and weary, in the flickering torchlight.',
 "13_into_the_dark": 'The same tunnel, torchlight bobbing: Thorin and the dwarves in a close line follow Bilbo, who leads the way down into the vast dark hall, one hand out ahead, torch held low and cautious; deep blackness ahead, a hint of pale glimmer far off.',
 "13_bilbo_finds_arkenstone": 'Atop a vast glittering mountain of gold and treasure inside a dark underground hall: small Bilbo stands alone, torch in one hand, transfixed by a great white jewel that glows with its own light at his feet, throwing rainbow sparks in every direction; far below, tiny points of torchlight mark the waiting dwarves at the tunnel mouth.',
 "13_bilbo_pockets_stone": 'Close on Bilbo atop the treasure pile: he kneels, both hands cupped around a glowing white jewel, eyes shut, about to slip it into the deepest pocket of his old jacket; torchlight throwing his shadow long across the gold.',
 "13_bat_scare": 'Near a huge broken gate at the far end of the underground hall, a gust of fresh air stirring: Bilbo stumbles backward, arms up, as a black bat swoops low past his face; his torch flies from his hand, tumbling, flame going out.',
 "13_gold_fever": 'A vast treasure hall lit by many torches: dwarves stand knee-deep in gold and jewels, stuffing pockets, trying on ancient armor; Fili and Kili, delighted, pluck golden harps with silver strings; Thorin nearby searches intently among the piles, not joining the music, his face distracted.',
 "13_mithril_coat": 'In the torchlit treasure hall, Thorin holds out a small, gleaming silver-grey coat of mail and a jeweled belt to Bilbo, who reaches for it with both hands, eyes wide with wonder; other dwarves look on, some still admiring armor and weapons around them.',
 "13_front_gate_daylight": 'A huge ruined archway at the end of a stone passage, cold daylight pouring through, bats fluttering overhead: the company of dwarves, cloaks thrown hastily over hidden armor, and small Bilbo step out into the light, stopping to stare at the valley of Dale spread below, wind in their hair.',
 "13_ravenhill_camp": "A windswept stone platform on the mountain's shoulder at dusk, an old doorway cut into the rock behind: the tired company makes camp, unpacking bundles; a few dwarves sit at the doorway scanning the sky, where distant flocks of birds wheel against the darkening clouds; Bilbo sits close to the door, exhausted.",

 # --- Chapter 14, planned 2026-09-16 against the condensed text; STUBS ONLY (placeholder art, no AI generation yet). ---
 "14_town_sees_light": 'Night over Lake-town: a few townsfolk lean on a snowy railing along the dark water, pointing up at a brief orange flash lighting the distant black shape of the Lonely Mountain on the horizon; worried and hopeful faces in torchlight.',
 "14_dragon_attacks": 'Night sky over the wooden lake-town: Smaug swoops low and huge over the rooftops, wings spread, breathing a jet of fire; below, the wooden bridge to shore has been hacked away, and archers on rooftops and balconies loose a hail of black arrows up at him, some bursting into sparks against his armored scales.',
 "14_town_burns": 'Lake-town ablaze at night, thatched roofs and wooden walls engulfed in orange flame reflected in the black water; people wade and swim for boats crowded with women and children on the market square; in the foreground a fat man in a fur-trimmed robe scrambles into a gilded boat, panic on his face.',
 "14_bard_last_arrow": 'Amid burning buildings, a tall grim bowman in plain grey clothes stands alone on a collapsing rooftop, his last black arrow nocked on a great bow, flames close on every side; an old black thrush has just landed on his shoulder, leaning to his ear as if speaking.',
 "14_black_arrow_strike": "Night sky lit by a huge full moon: Smaug banks low over the burning water, his pale jeweled belly catching the moonlight with one dark unguarded patch; a single black arrow streaks up from below and strikes home exactly there, the dragon's whole body convulsing in the flash.",
 "14_smaug_falls": 'Smaug plummets from the night sky toward the burning town below, wings crumpled, a trail of sparks and smoke behind him, moonlight and firelight mixing on the black water; small distant figures of townsfolk in boats look up in awe.',
 "14_survivors_mourn": 'Dawn on a crowded, shivering group of survivors gathered on the western shore of a lake, wrapped in blankets, watching the smoking ruins of their town across the water; a few boats loaded with rescued belongings float nearby; grim, weary faces in grey morning light.',
 "14_elves_march_to_lake": 'A long column of elvish spearmen and archers in green and brown marching briskly along a riverbank under a grey sky, banners raised; in the distance, smoke still rising faintly from the direction of a lake.',

 # --- Chapter 15, planned 2026-09-16 against the condensed text; STUBS ONLY (placeholder art, no AI generation yet). ---
 "15_watching_birds": "Bilbo and a few dwarves atop a newly built stone wall across the Mountain's Front Gate, scanning a sky thick with circling birds - starlings, finches, and high above, dark wheeling vultures; Thorin stands frowning at the sky, hand shading his eyes.",
 "15_old_thrush_returns": 'Close scene on the grassy shelf-like wall top: an old black speckle-breasted thrush perches on a stone beside Bilbo and Balin, head cocked, chattering rapidly; Balin leans in, puzzled, trying to understand.',
 "15_roac_arrives": 'An ancient, enormous raven with thin grey-flecked feathers and half-blind eyes lands heavily before Thorin and Balin on the stone wall, folding its wings with dignity; the thrush perches nearby watching; Bilbo stands close, listening intently.',
 "15_treasure_now_ours": 'Dwarves atop the wall throwing their arms up in wild celebration, hugging each other, some jumping - Thorin at the center laughing with relief, sky full of wheeling birds above them.',
 "15_gate_wall_built": "An empty, silent mountainside: the Front Gate transformed by a tall new wall of rough-hewn stone blocking the entrance completely, no door, only arrow-slits, with makeshift ladders leaning against it and ropes for hauling goods; a wide still reflecting pond fills the space in front, leaving only a narrow ledge along one side. No people or creatures anywhere in the scene, an empty architectural landscape shot.",
 "15_distant_campfires": "Night view from the Mountain's wall: far off across the dark valley near the ruins of Dale, a scatter of campfires and torches glows, faint sounds of a growing camp; Balin, arms on the parapet, watches grimly beside Bilbo.",
 "15_armies_arrive": 'Dawn light on a wide stony valley below the Mountain: a long column of armored elvish spearmen and Lake-town men in mail, carrying green and blue banners, climb a scree slope toward a waterfall, stopping in surprise before an unexpected stone wall and pond blocking the Gate.',
 "15_dwarves_song": 'Torchlit scene at the Gate, dwarves gathered on the wall with recovered golden harps, singing together with raised fists, Thorin at the center looking proud and fierce; firelight glinting off treasure and armor; small Bilbo sits apart, looking troubled.',
 "15_bard_parley": "Two groups face each other across a pond before the Mountain's Gate wall: on one side Thorin alone atop the wall, arms crossed; on the other, at the water's edge, tall grim Bard beside the golden-haired Elvenking, green and blue banners behind them.",
 "15_herald_demand": "A herald with a trumpet stands before the stone wall at the Gate, shouting up a formal demand, parchment in hand; behind him ranks of armored elves and men wait with banners; atop the wall, Thorin's face is thunderous.",
 "15_thorin_shoots_arrow": "Dramatic action: Thorin, atop the stone wall, draws his short horn bow and looses an arrow that thuds into the herald's raised shield below; the herald recoils in shock, men and elves behind him reaching for weapons in alarm.",

 # --- Chapter 16, planned 2026-09-16 against the condensed text; STUBS ONLY (placeholder art, no AI generation yet). ---
 "16_arkenstone_hidden": 'Thorin in the torchlit treasure hall, gesturing insistently to a few dwarves searching through piles of gold and jewels; unnoticed in the shadows nearby, Bilbo sits on a low pile of coins, one hand resting protectively over his own jacket pocket, worried expression.',
 "16_bombur_watch": 'Cold night atop the stone wall at the Gate: fat Bombur, wrapped in a cloak, sits hunched and shivering on watch; beside him Bilbo talks quietly, a coiled rope half-hidden at his feet.',
 "16_bilbo_slips_away": 'Bilbo, alone, climbs down a rope on the outside of a stone wall into darkness, moving carefully; a small bundle wrapped in cloth is tucked into his jacket; stars overhead, a camp far below dotted with faint firelight.',
 "16_river_stumble": 'Bilbo mid-stumble in a shallow, fast-flowing stream at night, arms flailing, about to fall; elvish lanterns approaching through the dark just behind him, throwing long beams across the water.',
 "16_elves_capture": 'Elvish sentries in green and brown, lanterns raised, surround dripping-wet Bilbo who stands with hands up, an awkward embarrassed smile on his face, hobbit-sized and comic among the tall elves.',
 "16_arkenstone_reveal": 'Inside a firelit tent at night: Bilbo, wrapped in a blanket over his armor, holds up a glowing white jewel before the astonished faces of the golden-haired Elvenking and grim Bard, both leaning forward, firelight catching its rainbow sparkle.',
 "16_gandalf_reappears": "Night among the tents of a camp: an old man in a dark travelling cloak steps out from a tent doorway and claps a hand on small Bilbo's shoulder with a knowing smile, as elvish escorts look on in surprise; stars overhead.",
 "16_bilbo_climbs_back": 'Bilbo, exhausted, climbs the last few feet of a rope up the outside of a stone wall in pre-dawn light, a camp and river faint and misty behind him below.',

 # --- Chapter 17, planned 2026-09-16 against the condensed text; STUBS ONLY (placeholder art, no AI generation yet). ---
 "17_bard_delegation": "A small procession approaches the Mountain's Gate wall in morning light: the golden-haired Elvenking, grim Bard, and an old cloaked man carrying an iron-bound wooden chest, escorted by a few unarmed elves and men; Thorin stands alone atop the wall watching them come.",
 "17_arkenstone_ultimatum": 'Dramatic close moment at the Gate wall: the old cloaked man has opened an iron-bound chest, and brilliant white light streams from a glowing jewel held in his hands; below on the wall, Thorin stands frozen in shock and fury, fists clenched.',
 "17_torin_grabs_bilbo": 'Atop the stone wall: furious Thorin grips small Bilbo by the front of his jacket with both hands, lifting him half off his feet, face contorted with rage; nearby dwarves look on, shocked and uneasy, not intervening.',
 "17_gandalf_intervenes": 'An old cloaked figure below throws back plaid and hood to reveal Gandalf, staff raised and glowing, voice clearly commanding; atop the wall Thorin has frozen, lowering Bilbo back down, startled.',
 "17_ransom_offer": 'Thorin stands alone atop the Gate wall, arms spread wide in bitter concession, dwarves behind him with heads bowed; below, Bard and the Elvenking exchange a look, Gandalf beside them, a closed iron-bound chest at their feet.',
 "17_dain_army_arrives": 'Dawn light on the eastern ridge of the Mountain: a long column of stout, heavily armored dwarves in steel mail and iron helmets, forked beards tucked into their belts, marches swiftly down toward the valley, twin-bladed pickaxes over their shoulders, banners of the Iron Hills flying.',
 "17_dain_standoff": "Tense meeting on the valley floor: a handful of armored dwarves from Dain's column face Bard and a group of Lake-men and elves across a narrow strip of land by a river bend, weapons lowered but ready, both sides talking with hard expressions.",
 "17_storm_and_bats": 'Dramatic sky: a black storm cloud rolls over the Mountain, lightning flashing; beneath it, a second, denser black cloud approaches from the north, unmistakably a vast swarm of bats and shapes in flight, not windblown; below, small figures of dwarves, men and elves stare upward in alarm.',
 "17_gandalf_warns": 'Gandalf stands alone between two armed camps, arms raised, staff blazing like lightning in the gathering dark; men, elves and dwarves nearby stare at him in shock as he shouts a warning, the monstrous cloud of bats and goblins looming closer in the sky behind him.',
 "17_battle_valley": "Wide dramatic battle scene in the valley between the Mountain's spurs: ranks of elvish archers and spearmen charging down a slope into a chaotic mass of small, fierce goblins on wolves, banners and weapons clashing, arrows in flight, dust and motion everywhere.",
 "17_thorin_bursts_out": 'A stone wall breaking open in a shower of rubble into a pond below: Thorin strides out at the head of his dwarves, no cloaks now, in full shining armor, eyes blazing, greataxe raised high, gold catching the stormy light as he roars a battle cry.',
 "17_eagles_arrive": 'High on a rocky ledge above a battle, Bilbo lies half-risen on the stones, pointing up in wonder at a red sunset breaking through storm clouds, where a great host of eagles streams in from the west, wings dark against the fiery sky; the battle rages small and distant far below.',

 # --- Chapter 18, planned 2026-09-16 against the condensed text; STUBS ONLY (placeholder art, no AI generation yet). ---
 "18_bilbo_wakes_alone": 'Bilbo lies alone on the flat frosty stones of a mountain outcrop in cold morning light, dazed, sitting up slowly and rubbing his head; the valley below is empty and silent, distant smoke rising, no one else in sight.',
 "18_soldier_finds_bilbo": 'A tired soldier in dented armor picks his way through the rocks and stops, startled, turning to look around at an apparently empty spot where a voice called out; small Bilbo, mid-pulling off his ring, becomes visible right in front of him, waving.',
 "18_carried_to_camp": 'A soldier walking carefully across a battlefield toward a distant camp of tents in a valley, small Bilbo cradled in his arms, wrapped and limp with exhaustion; the grim aftermath of battle visible in the distance, nothing graphic.',
 "18_gandalf_reunion": 'Outside a large tent in a ruined town, Gandalf, his arm in a sling, breaks into a delighted smile as he sees small Bilbo being set down before him; warm relief on both faces.',
 "18_thorin_farewell": "Inside a dim tent, Thorin lies on a pallet, battered armor and a notched axe on the floor beside him, his face pale but peaceful; small Bilbo kneels close by his side, head bowed in sorrow, one hand near Thorin's; Gandalf stands respectfully in the shadows behind.",
 "18_beorn_rescue": 'Dramatic battle memory: an enormous black bear rears up among scattering goblins and wolves, swatting them aside like leaves, carrying an unconscious armored dwarf gently in one great paw as he breaks through the encircling enemy.',
 "18_treasure_farewell_gifts": 'Inside a tent, Bard kneels presenting two small iron-bound chests, one glinting gold and one silver, to Bilbo, who holds up a hand in polite refusal with a small smile; a sturdy pony waits nearby ready to carry the modest load.',
 "18_dwarves_goodbye": "Before the Mountain's broken Gate, a line of dwarves bow low and solemn toward small Bilbo, who stands facing them with a hand raised in farewell, eyes a little wet; the Mountain rising grand behind them.",
 "18_journey_with_beorn": "A sunlit road through green hills: Gandalf and small Bilbo ride side by side on ponies, the golden-haired Elvenking's company visible nearby, and off to one side Beorn walks in human form, laughing, a huge friendly figure among the travelers.",
 "18_beorns_house_winter": "A warm, firelit great hall at Beorn's house in midwinter: Gandalf and Bilbo sit at a long table loaded with food among a cheerful gathered crowd, firelight glowing, snow visible through a window, festive and cozy mood.",

 # --- Chapter 19, planned 2026-09-16 against the condensed text; STUBS ONLY (placeholder art, no AI generation yet). ---
 "19_rivendell_return": 'Evening light on a steep wooded path down into a green valley: Gandalf and small Bilbo lead two tired ponies down the trail, an elegant house glimpsed through the trees below, faint elvish singing drifting up.',
 "19_elrond_fireside_tale": 'A warm firelit hall: Elrond listens attentively as Gandalf tells a story with animated gestures; small Bilbo dozes gently in a cushioned chair nearby, head nodding, half asleep.',
 "19_moonlit_lullaby": 'Bilbo leaning out of an open window at night, moonlight streaming in, listening with a sleepy smile to elves singing and dancing softly on a riverbank below, silver light on the water.',
 "19_troll_gold_dig": 'A sunny green roadside clearing: Gandalf and Bilbo kneel together digging up an old buried chest, dirt and roots around the hole, ponies grazing nearby, a bright ordinary daytime mood.',
 "19_homeward_road": 'Bright green early-summer countryside, a dirt road winding through hills: Gandalf on a tall horse and small Bilbo on a pony, laden saddlebags of gold, ride side by side toward the horizon, cheerful golden light.',
 "19_bilbo_sees_the_hill": 'Bilbo standing alone on a grassy hilltop, one hand shading his eyes, gazing at a distant green hill with a round door dotted among trees in the golden evening light; Gandalf a little behind on his horse, watching him with a curious smile.',
 "19_auction_chaos": "A comic, busy scene at Bilbo's round green front door: a crowd of hobbits carrying furniture and crates bustles in and out without wiping their feet, a blank unmarked notice board with no writing pinned to the gate; small dusty Bilbo stands in the doorway, hands on hips, utterly astonished.",
 "19_home_at_last": 'Cozy interior of a hobbit-hole years later: an older, comfortably plump Bilbo sits by a crackling fire in a round room full of books and treasures, a sword hanging above the mantel, writing contentedly at a desk with a quill.',
 "19_balin_visits": 'Warm firelit round room: Bilbo and an elderly dwarf with a long white beard and jeweled belt sit together in comfortable armchairs by the fire, deep in cheerful conversation, tea and pipes in hand, utterly at home.',

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
 "08_bilbo_vs_spider": "Dim green forest gloom: Bilbo, still half wrapped in thick grey spider silk around his legs, stands over a giant spider as big as he is, striking at its cluster of eyes with his small elvish dagger that glows pale blue; the spider rears back on its hairy legs, startled; sticky threads hang from the branches all around; Bilbo's face fierce and determined; dramatic but not gory, no blood.",
 "08_cocoons": "A dark part of the forest thick with black webs: a high branch from which a dozen grey silk cocoons hang in a row like huge bundles, with a dwarf's boot, a nose tip, a bit of beard or the corner of a colorful hood poking out of each; a fat spider on the branch pinches the nose sticking out of the biggest cocoon (Bombur), and a foot bursts out and kicks it; other giant spiders sit around on the webs; far below on the forest floor Bilbo, invisible, is only a faint transparent outline peering up in horror.",
 "08_stones_and_song": "Forest floor among huge tree trunks and webs: Bilbo, shown as a faint half-transparent ghostly outline because he wears the ring, is caught mid-throw hurling an egg-sized stone, mouth open in song; one giant spider tumbles head over heels off a branch, another crashes through a torn web; a crowd of furious spiders rushes toward the wrong tree, their many eyes glaring; a dry stream bed full of pebbles at Bilbo's feet.",
 "08_battle_under_tree": "Under the cocoon tree in the gloom: twelve exhausted dwarves in tattered hoods, still trailing bits of grey silk, stand back to back with sticks, knives and stones - Bombur held upright between his brother Bofur and cousin Bifur; small Bilbo leaps in front of them slashing at spiders with his glowing dagger, cutting strands of web; a ring of hundreds of giant spiders on the ground and on the branches around them; frantic but not gory.",
 "08_bilbo_vanishes": "In the middle of the spider-ringed dwarves: Bilbo, holding up his hand with a small gold ring, is half faded into transparency, in the very act of disappearing; the dwarves nearest him - Balin with white beard and scarlet hood, Fili and Kili in blue hoods - stare with mouths open and eyes popping in astonishment; spiders spinning webs from tree to tree behind them; gloomy forest light.",
 "08_thorin_before_king": "A great cavern hall lit by lanterns, its pillars carved like tree trunks, an underground river glinting through the gate: the Elvenking sits on a carved wooden throne with a crown of autumn leaves and berries, golden-haired, stern, holding a carved oak staff; before him stands Thorin, hands bound with rope, hood torn, lips pressed shut in stubborn silence; tall elf guards with spears and long bows on either side.",
 "08_thorin_cell": "A small stone cell deep in the caves under the palace with a heavy oak door and a tiny barred window: Thorin sits on a straw bed, his sky-blue hood pulled down, chin on his fist, brooding; beside him on the floor a loaf of bread, a piece of cheese and a jug of water, untouched; the light of a single lantern; quiet, thoughtful mood.",
 # --- Chapter 9 (Barrels out of bond), planned 2026-09-12 against the condensed text (10.8k chars): 11 windows, best moment per window.
 # Bilbo: no hood or cloak, green waistcoat, small elvish dagger at his belt; he wears the ring almost the whole chapter, so wherever
 # elves or dwarves are around he is drawn as a faint half-transparent outline; he is visible only when alone (on the barrel in the river).
 # Twelve dwarves (Thorin is held separately until the cells): ragged, torn hoods, no packs, on foot. Gandalf is NOT in this chapter.
 # Avoid the words "himself/itself" in these prompts: the CHARS injection matches "elf" inside them.
 "09_bridge_gate": "Night in the deep forest, torches burning like red stars: a line of twelve ragged dwarves in torn colorful hoods, blindfolded and roped together, is led by tall wood-elves with spears and bows across a stone bridge over a fast black river toward huge gates in a steep wooded hillside, torchlight on the water; at the very end of the line, a few steps behind the last elf, Bilbo is drawn only as a faint half-transparent outline hurrying to keep up; giant beech trees lean over the bank.",
 "09_balin_before_king": "A great cavern hall lit by red torches, its pillars carved from the living rock: the Elvenking sits on a carved wooden throne with a crown of red autumn leaves and berries, an oak staff in his hand, frowning; before him stand twelve tired ragged dwarves in torn hoods, ropes just taken off their wrists; in front of them old Balin with a white beard and scarlet hood steps forward, chin up, one hand raised, boldly answering the king; elf guards with spears on both sides; nobody else in the picture.",
 "09_keyhole": "A dim stone corridor deep under the palace caves, a single torch in a bracket far away: a heavy oak door with iron bands and a big keyhole; Bilbo, drawn as a faint half-transparent outline, kneels at the door with his mouth to the keyhole, one hand cupped beside it, whispering; the corridor is empty and quiet; dramatic close view, mysterious but warm light.",
 "09_cellar_trapdoor": "The wine cellar of the elf palace, a vaulted stone room lit by lanterns and stacked with big wooden barrels of every size: in the floor a large square oak trapdoor stands open, and through it far below gleams a dark rushing underground stream; two wood-elves in green and brown roll an empty barrel toward the opening; peeking out from behind a stack of barrels in the foreground, Bilbo is a faint half-transparent outline, eyes wide, watching and thinking.",
 "09_keys": "Inside the cellar at night, a wooden table with two huge earthen jugs and cups: the chief of the guards, a tall elf in green and brown, sleeps with his head on his arms on the table, and the butler Galion snores in his chair beside him with a happy smile; a big ring of iron keys hangs from the sleeping chief's belt, and Bilbo, drawn as a faint half-transparent outline, stands on tiptoe next to him, both hands on the key ring, lifting it off with a tense, held-breath face; one candle flame lights the scene.",
 "09_thorin_freed": "A low dark corridor of the deepest dungeon, lit by one lantern: Bilbo, a faint half-transparent outline, has just unlocked a heavy oak door with a big iron key from a large jangling bunch; Thorin, gaunt, in his torn sky-blue hood, steps out of the cell with an astonished grateful face and a hand on his heart; behind Bilbo, crowding the narrow corridor, the other twelve dwarves in ragged hoods, Balin with white beard and scarlet hood in front, all peering forward, fingers on lips.",
 "09_into_barrels": "The cellar with rows of big empty wooden barrels standing on end: several dwarves are already climbing into barrels, only hoods and beards showing over the rims; in the middle Thorin twists and squirms to fit into his barrel like a big dog in a small kennel, sky-blue hood askew; old Balin with a white beard and scarlet hood, up to his shoulders in the next barrel, points at the lid and complains; Bilbo, a faint half-transparent outline, hurries past with an armful of straw; lantern light, comic and busy.",
 "09_last_barrel": "Dramatic moment in the cellar: a group of merry wood-elves in green and brown, singing and laughing, roll barrels toward a dark open trapdoor in the floor and tip them in one after another; the very last barrel is already tilting over the edge into the black water below, and Bilbo, a faint half-transparent outline, clings to it desperately with both arms and legs, curly hair flying, about to drop through the hole; splashes rise from the dark stream; lanterns on the walls.",
 "09_riding_barrel": "Night on a fast dark forest river under overhanging branches, a scatter of stars between the leaves: a crowd of wooden barrels bobs and spins in the rushing water; on top of one big barrel Bilbo lies sprawled flat on his stomach like a wet rat, arms and legs spread wide, gripping the rim, soaked curly hair and green waistcoat dripping, teeth chattering but hanging on; some barrels ride low in the water; Bilbo is the only figure in the picture.",
 "09_bilbo_sneeze": "Night at the forest's edge by the river: in the background a small wooden hut, a campfire and a few wood-elves in green and brown looking around in puzzlement with lanterns; in the foreground, hidden under a bush of autumn leaves, Bilbo is drawn as a faint half-transparent outline caught mid-sneeze, eyes shut, mouth wide open, hugging a loaf of bread, a leather wine flask and a round pie; a trail of wet footprints leads from the river to the bush.",
 "09_raft_dawn": "Grey dawn on a wide river at the edge of a dark forest, pale sky and mist over the water: a big raft made of many barrels roped together, riding low in the water, is pushed off from a pebbly shore by wood-elves standing knee-deep in the river with long poles, one elf at the front calling and pointing downstream; perched on top of the barrels among the ropes, Bilbo is a faint half-transparent outline hugging his knees, red-nosed and shivering; the river runs away eastward toward open country and a far grey lake.",
}

def gen(name, prompt):
    ch, slug = name.split("_", 1)
    out = pathlib.Path(f"{int(ch):02d}") / "img" / f"{slug}.png"  # chapter dir NN/img/
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
unknown = [n for n in ONLY if n not in SCENES]
if unknown:
    sys.exit("no such scene in SCENES: " + ", ".join(unknown))

todo = [(k, v) for k, v in SCENES.items() if not ONLY or k in ONLY]

if DRY:
    # The keyword dump CLAUDE.md asks for, before any prompt reaches the API.
    for name, scene in todo:
        trace = []
        text = full_prompt(scene, name, trace)
        print(f"\n=== {name} ===\nCHARS injected: {', '.join(trace) or '(none)'}\n{text}")
    print(f"\n{len(todo)} scene(s), dry run, nothing generated, $0 spent.")
    sys.exit(0)

print(f"{len(todo)} picture(s) to generate, ~${0.065 * len(todo):.2f} at medium 1536x1024.", flush=True)
with concurrent.futures.ThreadPoolExecutor(4) as ex:
    for name, st in ex.map(lambda kv: gen(*kv), todo):
        print(name, st, flush=True)
