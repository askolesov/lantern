# Chapter 3 (condensed text, 9946 chars) — 12 picture slots, planned against the paragraph each picture
# lands next to (build.py spreads pictures by character count; slot -> paragraph index of chapters.json ch.3
# after split_long). Format as in scenes_4_10.py: (slug, english prompt, russian caption), in story order.
# Not generated yet (needs user approval + OPENAI_API_KEY). When approved: copy into SCENES of gen_images.py
# as "3_<slug>", put (slug, caption) pairs into scenes[2] in build.py, then gen_images -> shrink -> build.
S = {
3: [
 # 1 -> para 0: riding in silence for days, camping under the open sky, ponies grazing
 ("silent_ride", "Gandalf on a white horse leading Bilbo on a small pony and a long line of dwarves on ponies in silence across wild empty hills under a grey overcast sky, nobody singing, tired faces, tall grass, a low campfire smoke from last night's camp far behind them.", "Молча через пустоши"),
 # 2 -> para 4 (3-4): Balin explains these are only the Misty Mountains' foothills; Bilbo is terribly tired, dreams of his armchair
 ("balin_mountains", "Balin pointing with his whole arm at huge grey mountains close ahead, their snowy peaks shining above dark slopes; Bilbo the hobbit slumped wearily on a rock beside his pony, staring up at the peaks with wide tired eyes; other dwarves resting with the ponies; morning sun.", "Это та самая Гора?"),
 # 3 -> para 10: crossing the moorland all morning; sudden ravines with waterfalls, bogs with bright flowers
 ("ravines", "The company on ponies halted at the edge of a sudden narrow ravine cut into flat stony moorland, a small waterfall and a stream with trees far down inside it; nearby a green bog with tall bright flowers; grey mountains on the horizon; bright noon light.", "Лощины и водопады"),
 # 4 -> para 13 (12-13): dusk, Gandalf finds the cliff edge; the deep valley of Rivendell with a light on the far slope
 ("valley_found", "Dusk with the first stars; Gandalf on his horse at the edge of a steep cliff, pointing down with his staff into a deep hidden valley full of trees, a rushing stream at the bottom, one warm golden light glowing on the far slope; Bilbo and the dwarves on ponies crowding behind him and peering over the edge.", "Наконец-то! Вот она!"),
 # 5 -> para 16 (15-18): night, blue stars, elves' song bursts from the trees
 ("elf_song", "Night in a wooded valley by a stream, stars shining bright blue; Bilbo on his pony looking up amazed; laughing elves sitting in the branches of tall trees above the path, singing, small lanterns hanging in the trees; dwarves on ponies below looking grumpy.", "Песня в деревьях"),
 # 6 -> para 21 (20-22): elves peek out and tease Bilbo on his pony; a tall young elf comes out and bows
 ("elves_tease", "Elves stepping out from behind trees in the dark forest, pointing and laughing kindly at Bilbo the hobbit sitting on his small pony, Bilbo blushing and smiling shyly; a tall young elf bowing gracefully to Gandalf and Thorin; Thorin frowning with folded arms; lantern light.", "Только взгляните!"),
 # 7 -> para 27 (27-29): the narrow stone bridge without rails; Thorin bent double, beard over the foam; elves with lamps
 ("bridge", "Night; a very narrow stone bridge with no railings over a foaming mountain river; Thorin leading his pony across, bent almost on all fours with his long beard dangling over the white foam; elves on the bank holding bright lamps, laughing and singing; Bilbo and the other dwarves waiting their turn with their ponies.", "Папаша, не макай бороду!"),
 # 8 -> para 32 (31-34): two happy weeks in the Last Homely House; Elrond the master
 ("elrond_house", "The Last Homely House: a beautiful timbered house with tall windows glowing warm gold, big front doors standing wide open, in a forest valley beside a waterfall at evening; Elrond on the doorstep welcoming Bilbo, Gandalf and the dwarves, who lead their ponies up the path.", "Последний Гостеприимный Дом"),
 # 9 -> para 36 (36-37): Elrond reads the runes on the two troll-hoard swords, Orcrist and Glamdring
 ("swords", "A sunny hall with tall arched windows; Elrond holding up two ancient elven swords with ornate hilts, studying the runes on the blades; Thorin and Gandalf watching closely, Bilbo peeking curiously from behind them.", "Оркрист и Гламдринг"),
 # 10 -> para 41 (38-42): Thorin looks at his sword with new interest, vows to keep its fame
 ("thorin_sword", "Thorin standing proudly with his ancient elven sword raised before him, admiring the shining blade with new respect; Elrond beside him with a calm, slightly worried expression; a stone terrace with mountains behind, late afternoon light.", "Торин и Оркрист"),
 # 11 -> para 47 (43-48): Elrond holds the map up to the young moon; silvery moon-letters appear; everyone leans in
 ("moon_letters", "Night on an open terrace under a bright crescent moon; Elrond holding an old parchment map up against the moonlight; faint silvery magical marks shimmering on the parchment (abstract glowing shimmer, no readable letters); Bilbo, Thorin and Gandalf leaning in with wide eyes.", "Лунные буквы"),
 # 12 -> para 54: midsummer morning departure, elves sing farewell, road to the mountains
 ("departure", "A bright fresh midsummer morning, cloudless blue sky, sunlight sparkling on the river; Bilbo, Gandalf and the dwarves riding out of the green valley on ponies toward the misty mountains; elves waving and singing farewell from the trees and the bridge.", "Утро Солнцеворота"),
],
}
