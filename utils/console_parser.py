import re

console_match = re.compile(r"PR:SetSelectedHero.*\((?P<id>\d+)\)$", re.M)

def parse_heroes(console_text: str) -> list:
    return console_match.findall(console_text)



if __name__ == "__main__":
    ids = parse_heroes("""[Server] PR:SetSelectedHero 0:[U:1:12030109] npc_dota_hero_nevermore(11)
        [Server] PR:SetSelectedHero 1:[I:0:0] npc_dota_hero_lion(26)
        [Server] PR:SetSelectedHero 2:[I:0:0] npc_dota_hero_bane(3)
        [Server] PR:SetSelectedHero 3:[I:0:0] npc_dota_hero_oracle(111)
        [Server] PR:SetSelectedHero 4:[I:0:0] npc_dota_hero_axe(2)
        [Server] PR:SetSelectedHero 5:[I:0:0] npc_dota_hero_bloodseeker(4)
        [Server] PR:SetSelectedHero 6:[I:0:0] npc_dota_hero_weaver(63)
        [Server] PR:SetSelectedHero 7:[I:0:0] npc_dota_hero_spectre(67)
        [Server] PR:SetSelectedHero 8:[I:0:0] npc_dota_hero_viper(47)
        [Server] PR:SetSelectedHero 9:[I:0:0] npc_dota_hero_brewmaster(78)
        """)

    pass