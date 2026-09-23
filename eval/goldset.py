"""
Gold set for evaluating the resolver/retriever - naturally-phrased
questions, each keyed to the achievement (api_name) a person asking
that question is actually looking for.

Starter batch - Claude drafted these from the real achievement data in
ingest/cache/schema_976730.json (every answer_api_name below is copied
from that file, not guessed), for you to edit, cut, reword, or add to
before this becomes the actual eval set. This is meant to read like
your judgment call on what "naturally phrased" means, not mine.

"phrasing" on each entry is one of three tiers:
  "exact_name"  - the question basically names the achievement. This is
                   what the resolver's exact/fuzzy name match should
                   catch almost for free.
  "rephrased"   - describes the achievement's requirement in different
                   words than Steam's own description, without naming
                   the achievement itself.
  "vague"       - indirect enough that answering it probably needs real
                   retrieval (embeddings + guide text), not just a name
                   or description match.

Tracking this per question is what lets you measure the brief's central
question later: how many questions the resolver alone can answer, versus
how many actually need the retrieval path to kick in.

This file just defines data - eval/metrics.py (or whatever scores this)
imports GOLD_SET from here. Nothing in this module runs anything.
"""

GOLD_SET = [
    {
        "question": "What do I need to do for the Life Story achievement?",
        "answer_api_name": "1_0_LIFE_STORY",
        "phrasing": "exact_name",
    },
    {
        "question": "How do I finish the Master Chief Saga playlist?",
        "answer_api_name": "1_0_LIFE_STORY",
        "phrasing": "rephrased",
    },
    {
        "question": "How many enemies do I need to kill for Just Getting Started?",
        "answer_api_name": "1_1_JUST_GETTING_STARTED",
        "phrasing": "exact_name",
    },
    {
        "question": "How do I unlock Balaho's Most Wanted?",
        "answer_api_name": "1_2_BALAHOS_MOST_WANTED",
        "phrasing": "exact_name",
    },
    {
        "question": "What's the achievement for killing a ton of Grunts?",
        "answer_api_name": "1_2_BALAHOS_MOST_WANTED",
        "phrasing": "vague",
    },
    {
        "question": "How many Elites do I have to kill for the achievement?",
        "answer_api_name": "1_3_THE_ONE_PERCENT",
        "phrasing": "rephrased",
    },
    {
        "question": "What's The One Percent achievement for?",
        "answer_api_name": "1_3_THE_ONE_PERCENT",
        "phrasing": "exact_name",
    },
    {
        "question": "Is there an achievement for killing Jackals?",
        "answer_api_name": "1_4_SPOILSPORT",
        "phrasing": "vague",
    },
    {
        "question": "What do I need to do to get Going Bananas?",
        "answer_api_name": "1_5_GOING_BANANAS",
        "phrasing": "exact_name",
    },
    {
        "question": "How many Brutes do I need to kill for Going Bananas?",
        "answer_api_name": "1_5_GOING_BANANAS",
        "phrasing": "rephrased",
    },
    {
        "question": "How many Hunters do I need to kill for Hunters Hunted?",
        "answer_api_name": "1_6_HUNTERS_HUNTED",
        "phrasing": "exact_name",
    },
    {
        "question": "What's the achievement for killing 100 of the little floating drone enemies?",
        "answer_api_name": "1_7_CHECKMATE",
        "phrasing": "vague",
    },
    {
        "question": "How do I get 'I Was Wondering What Would Break First'?",
        "answer_api_name": "1_8_I_WAS_WONDERING_WHAT_WOULD_BREAK_FIRST",
        "phrasing": "exact_name",
    },
    {
        "question": "How many Crawlers do I need to kill for Pest Control?",
        "answer_api_name": "1_9_PEST_CONTROL",
        "phrasing": "exact_name",
    },
    {
        "question": "What do I need for Pest Control?",
        "answer_api_name": "1_9_PEST_CONTROL",
        "phrasing": "exact_name",
    },
    {
        "question": "What do I need for Thanks A Killion?",
        "answer_api_name": "1_10_THANKS_A_KILLION",
        "phrasing": "exact_name",
    },
    {
        "question": "How many medals do I need to collect for Medal Completionist?",
        "answer_api_name": "1_11_MEDAL_COMPLETIONIST",
        "phrasing": "exact_name",
    },
    {
        "question": "Is there an achievement just for dying to the Guardians?",
        "answer_api_name": "1_12_THE_GUARDIANS_ARE_COMING",
        "phrasing": "vague",
    },
    {
        "question": "How do I get the Headhunter achievement?",
        "answer_api_name": "3_20_HEADHUNTER",
        "phrasing": "exact_name",
    },
    {
        "question": "How do I find every skull in Halo CE?",
        "answer_api_name": "3_20_HEADHUNTER",
        "phrasing": "rephrased",
    },
    {
        "question": "What do I get for beating Halo CE on Normal?",
        "answer_api_name": "3_21_BIRTH_OF_A_SPARTAN",
        "phrasing": "rephrased",
    },
    {
        "question": "How do I unlock Birth of a Spartan?",
        "answer_api_name": "3_21_BIRTH_OF_A_SPARTAN",
        "phrasing": "exact_name",
    },
    {
        "question": "How do I beat every level of Halo CE on Heroic?",
        "answer_api_name": "3_22_BELIEVE_IN_A_HERO",
        "phrasing": "rephrased",
    },
    {
        "question": "What's required for Living Legend?",
        "answer_api_name": "3_23_LIVING_LEGEND",
        "phrasing": "exact_name",
    },
    {
        "question": "how do i beat halo ce on legendary",
        "answer_api_name": "3_23_LIVING_LEGEND",
        "phrasing": "rephrased",
    },
    {
        "question": "How do I beat The Pillar of Autumn on Legendary without grabbing an overshield?",
        "answer_api_name": "3_24_OVERSHIELDS_ARE_FOR_SISSIES",
        "phrasing": "rephrased",
    },
    {
        "question": "Is there an achievement for not using any health packs on the first level of CE?",
        "answer_api_name": "3_25_WALK_IT_OFF",
        "phrasing": "vague",
    },
    {
        "question": "What do I need to do for How Pedestrian?",
        "answer_api_name": "3_26_HOW_PEDESTRIAN",
        "phrasing": "exact_name",
    },
    {
        "question": "How do I beat the level Halo without getting in a vehicle?",
        "answer_api_name": "3_26_HOW_PEDESTRIAN",
        "phrasing": "rephrased",
    },
    {
        "question": "Is there an achievement for not dying on The Library?",
        "answer_api_name": "3_27_THAT_JUST_HAPPENED",
        "phrasing": "vague",
    },
    {
        "question": "How do I beat Two Betrayals on Legendary without killing a single Grunt?",
        "answer_api_name": "3_28_LOOK_OUT_FOR_THE_LITTLE_GUYS",
        "phrasing": "rephrased",
    },
    {
        "question": "What's Look Out for the Little Guys for?",
        "answer_api_name": "3_28_LOOK_OUT_FOR_THE_LITTLE_GUYS",
        "phrasing": "exact_name",
    },
    {
        "question": "What's the achievement Tying Up Loose Ends for?",
        "answer_api_name": "3_30_TYING_UP_LOOSE_ENDS",
        "phrasing": "exact_name",
    },
    {
        "question": "Is there an achievement for one-shotting a Hunter with the pistol?",
        "answer_api_name": "4_2_YOU_ARE_THE_WEAPON",
        "phrasing": "vague",
    },
    {
        "question": "How do I find all the skulls in Halo 2?",
        "answer_api_name": "6_24_TROPHY_COLLECTOR",
        "phrasing": "rephrased",
    },
    {
        "question": "How do I get Trophy Collector?",
        "answer_api_name": "6_24_TROPHY_COLLECTOR",
        "phrasing": "exact_name",
    },
    {
        "question": "Where's the Master Chief toy in Delta Halo?",
        "answer_api_name": "6_25_AND_SO_IT_BEGINS",
        "phrasing": "vague",
    },
    {
        "question": "What do I need for the Toybox achievement?",
        "answer_api_name": "7_2_TOYBOX",
        "phrasing": "exact_name",
    },
    {
        "question": "How many toys do I need to find in Halo 2?",
        "answer_api_name": "7_2_TOYBOX",
        "phrasing": "rephrased",
    },
    {
        "question": "What do I get for finishing Halo 2 on Normal?",
        "answer_api_name": "7_3_WARRIOR",
        "phrasing": "rephrased",
    },
    {
        "question": "How do I unlock the Warrior achievement?",
        "answer_api_name": "7_3_WARRIOR",
        "phrasing": "exact_name",
    },
    {
        "question": "Is there a Halo 2 achievement for beating it on Heroic?",
        "answer_api_name": "7_4_HERO",
        "phrasing": "vague",
    },
    {
        "question": "How do I unlock Legendary Anniversary?",
        "answer_api_name": "7_5_LEGENDARY_ANNIVERSARY",
        "phrasing": "exact_name",
    },
    {
        "question": "What do I get for beating Halo 3 on Normal?",
        "answer_api_name": "9_25_PROPHETS_BANE",
        "phrasing": "rephrased",
    },
    {
        "question": "What's Prophet's Bane for?",
        "answer_api_name": "9_25_PROPHETS_BANE",
        "phrasing": "exact_name",
    },
    {
        "question": "What's required for With Your Shield or On It?",
        "answer_api_name": "9_26_WITH_YOUR_SHIELD_OR_ON_IT",
        "phrasing": "exact_name",
    },
    {
        "question": "how do i beat halo 3 on legendary",
        "answer_api_name": "9_27_FINISHED_THE_FIGHT",
        "phrasing": "rephrased",
    },
    {
        "question": "Is there an achievement just for finishing the Halo 3 campaign on the hardest difficulty?",
        "answer_api_name": "9_27_FINISHED_THE_FIGHT",
        "phrasing": "vague",
    },
    {
        "question": "How do I beat Tsavo Highway without using a vehicle?",
        "answer_api_name": "9_28_BEGINS_WITH_A_SINGLE_STEP",
        "phrasing": "rephrased",
    },
    {
        "question": "What do I need for Begins with a Single Step?",
        "answer_api_name": "9_28_BEGINS_WITH_A_SINGLE_STEP",
        "phrasing": "exact_name",
    },
    {
        "question": "Is there a secret music easter egg achievement in Halo 3?",
        "answer_api_name": "10_0_DIRGE_OF_MADRIGAL",
        "phrasing": "vague",
    },
    {
        "question": "What's the Delicious Brains achievement for?",
        "answer_api_name": "10_11_DELICIOUS_BRAINS",
        "phrasing": "exact_name",
    },
    {
        "question": "Is there an achievement for killing a bunch of Flood?",
        "answer_api_name": "10_11_DELICIOUS_BRAINS",
        "phrasing": "vague",
    },
    {
        "question": "How many Hornet kills do I need in Halo 2 Anniversary multiplayer?",
        "answer_api_name": "12_26_SHOOK_THE_HORNETS_NEST",
        "phrasing": "rephrased",
    },
    {
        "question": "How do I get Shook the Hornet's Nest?",
        "answer_api_name": "12_26_SHOOK_THE_HORNETS_NEST",
        "phrasing": "exact_name",
    },
    {
        "question": "Is there an achievement for killing people launched from a man cannon?",
        "answer_api_name": "12_27_SKEET_SHOOTER",
        "phrasing": "vague",
    },
    {
        "question": "What do I need for the Zealot achievement?",
        "answer_api_name": "13_9_ZEALOT",
        "phrasing": "exact_name",
    },
    {
        "question": "How do I finish the Halo 3 LASO playlist?",
        "answer_api_name": "13_11_A_PREFERENCE_FOR_PAIN",
        "phrasing": "rephrased",
    },
    {
        "question": "What's required for Naked Tyrant?",
        "answer_api_name": "13_13_NAKED_TYRANT",
        "phrasing": "exact_name",
    },
    {
        "question": "How do I complete the Halo 4 LASO campaign?",
        "answer_api_name": "13_13_NAKED_TYRANT",
        "phrasing": "rephrased",
    },
    {
        "question": "Is there one achievement for getting every skull across CE, 2, and 3?",
        "answer_api_name": "13_15_THRONE_OF_BONES",
        "phrasing": "vague",
    },
    {
        "question": "What's the Throne of Bones achievement?",
        "answer_api_name": "13_15_THRONE_OF_BONES",
        "phrasing": "exact_name",
    },
    {
        "question": "What do I need to do for No Pain, No Gain?",
        "answer_api_name": "16_4_NO_PAIN_NO_GAIN",
        "phrasing": "exact_name",
    },
    {
        "question": "Where's the hidden skull on the Assembly map?",
        "answer_api_name": "16_6_ASSEMBLY_SKULL",
        "phrasing": "vague",
    },
    {
        "question": "What's the Assembly Skull achievement for?",
        "answer_api_name": "16_6_ASSEMBLY_SKULL",
        "phrasing": "exact_name",
    },
    {
        "question": "Where do I find the hidden skull on Citadel?",
        "answer_api_name": "16_9_CITADEL_SKULL",
        "phrasing": "rephrased",
    },
    {
        "question": "What's the Brainpan achievement for?",
        "answer_api_name": "16_12_BRAINPAN",
        "phrasing": "exact_name",
    },
    {
        "question": "How many different Halo 3 multiplayer maps do I need to play?",
        "answer_api_name": "16_17_WORLD_TRAVELER",
        "phrasing": "rephrased",
    },
    {
        "question": "How do I get World Traveler?",
        "answer_api_name": "16_17_WORLD_TRAVELER",
        "phrasing": "exact_name",
    },
    {
        "question": "What do I need to do for Going International?",
        "answer_api_name": "16_19_GOING_INTERNATIONAL",
        "phrasing": "exact_name",
    },
    {
        "question": "Where's the first audio log in ODST?",
        "answer_api_name": "16_23_LISTENER",
        "phrasing": "vague",
    },
    {
        "question": "Where do I find the 7th audio log in ODST?",
        "answer_api_name": "16_29_AUDITOR",
        "phrasing": "rephrased",
    },
    {
        "question": "What's the Give Heed achievement for?",
        "answer_api_name": "17_2_GIVE_HEED",
        "phrasing": "exact_name",
    },
    {
        "question": "What do I get for beating Reach on Normal?",
        "answer_api_name": "20_4_THE_SOLDIER_WE_NEED_YOU_TO_BE",
        "phrasing": "rephrased",
    },
    {
        "question": "What's required for The Soldier We Need You To Be?",
        "answer_api_name": "20_4_THE_SOLDIER_WE_NEED_YOU_TO_BE",
        "phrasing": "exact_name",
    },
    {
        "question": "How do I unlock Gods Must Be Strong?",
        "answer_api_name": "20_6_GODS_MUST_BE_STRONG",
        "phrasing": "exact_name",
    },
    {
        "question": "how do i beat reach on legendary",
        "answer_api_name": "20_6_GODS_MUST_BE_STRONG",
        "phrasing": "rephrased",
    },
    {
        "question": "How do I solo Reach on Legendary?",
        "answer_api_name": "20_7_A_MONUMENT_TO_ALL_YOUR_SINS",
        "phrasing": "rephrased",
    },
    {
        "question": "Is there an achievement for beating every par time in Reach?",
        "answer_api_name": "20_17_FAST_FALL",
        "phrasing": "vague",
    },
    {
        "question": "What's required for Canonical Conundrum?",
        "answer_api_name": "22_2_CANONICAL_CONUNDRUM",
        "phrasing": "exact_name",
    },
    {
        "question": "How many data pads do I need to find in Reach?",
        "answer_api_name": "22_2_CANONICAL_CONUNDRUM",
        "phrasing": "rephrased",
    },
    {
        "question": "How do I finish the Reach LASO playlist?",
        "answer_api_name": "22_3_WHY_DO_THIS_TO_YOURSELF?",
        "phrasing": "rephrased",
    },
    {
        "question": "What's the Reach Has Been Good to Me achievement?",
        "answer_api_name": "22_4_REACH_HAS_BEEN_GOOD_TO_ME",
        "phrasing": "exact_name",
    },
    {
        "question": "What do I get for finishing a Reach playlist?",
        "answer_api_name": "22_4_REACH_HAS_BEEN_GOOD_TO_ME",
        "phrasing": "rephrased",
    },
    {
        "question": "Is there an achievement tied to a specific date in Reach?",
        "answer_api_name": "22_6_REMEMBER_REACH",
        "phrasing": "vague",
    },
    {
        "question": "What do I need to do to complete a Firefight set?",
        "answer_api_name": "22_8_ENEMIES_EVERYWHERE",
        "phrasing": "rephrased",
    },
    {
        "question": "How do I get Enemies Everywhere?",
        "answer_api_name": "22_8_ENEMIES_EVERYWHERE",
        "phrasing": "exact_name",
    },
    {
        "question": "How do I get Left Behind?",
        "answer_api_name": "22_12_LEFT_BEHIND",
        "phrasing": "exact_name",
    },
    {
        "question": "What score do I need on Lone Wolf firefight for the achievement?",
        "answer_api_name": "22_12_LEFT_BEHIND",
        "phrasing": "rephrased",
    },
    {
        "question": "Is there an achievement for using the turret on a Pelican?",
        "answer_api_name": "22_15_JORGE_CANT_HAVE_ALL_THE_BIG_GUNS",
        "phrasing": "vague",
    },
    {
        "question": "Where's the hidden binary code easter egg in Reach?",
        "answer_api_name": "22_16_IM_SORRY_DAVE",
        "phrasing": "rephrased",
    },
    {
        "question": "What's the Meddling and Madness achievement for?",
        "answer_api_name": "21_27_MEDDLING_AND_MADNESS",
        "phrasing": "exact_name",
    },
    {
        "question": "Where's data pad 13 on Tip of the Spear?",
        "answer_api_name": "21_27_MEDDLING_AND_MADNESS",
        "phrasing": "rephrased",
    },
    {
        "question": "Where's data pad 17 on The Package?",
        "answer_api_name": "21_31_SILENT_SHEPHERDS",
        "phrasing": "rephrased",
    },
    {
        "question": "What's a Skullamanjaro and how do I get the achievement for it?",
        "answer_api_name": "22_9_NEGATIVE_GHOSTRIDER",
        "phrasing": "vague",
    },
    {
        "question": "How do I win an Invasion game in the first phase?",
        "answer_api_name": "22_10_SKUNKED",
        "phrasing": "rephrased",
    },
    {
        "question": "What's the Skunked achievement for?",
        "answer_api_name": "22_10_SKUNKED",
        "phrasing": "exact_name",
    },
    {
        "question": "What score do I need for One Final Firefight?",
        "answer_api_name": "22_13_ONE_FINAL_FIREFIGHT",
        "phrasing": "exact_name",
    },
    {
        "question": "How do I unlock One Final Firefight?",
        "answer_api_name": "22_13_ONE_FINAL_FIREFIGHT",
        "phrasing": "exact_name",
    },
    {
        "question": "Is there an achievement for killing a hidden elite commander in Reach?",
        "answer_api_name": "22_14_WHAT_ABOUT_BOB?",
        "phrasing": "vague",
    },
]
