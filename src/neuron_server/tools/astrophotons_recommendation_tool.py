
from langchain.tools import BaseTool
from pydantic import BaseModel, Field

astrophotons_recommendations = {
    "January": [
        "California Nebula (NGC 1499 / Sh2-220)",
        "Crab Nebula (M1 / NGC 1952) - check the Crab Nebula picture from the Hubble Space Telescope.",
        "Flame Nebula (NGC 2024 / Sh2-277)",
        "Flaming Star Nebula (IC 405 / SH 2-229 / Caldwell 31)",
        "Horsehead Nebula (Barnard 33)",
        "IC 342 Spiral Galaxy (Caldwell 5)",
        "NGC 1907 Open Cluster",
        "Orion Nebula (M42 / NGC 1976) - the best nebula to start. It's bright, vast, and colorful.",
        "Pleiades Star Cluster (M45) - so bright that it is visible to the naked eye.",
        "Running Man Nebula (NGC 1977 / Sh2-279)",
        "Starfish Cluster (M38 / NGC 1912)",
        "Tadpole Nebula (NGC 1893 / IC 410)",
        "Witch Head Nebula (IC 2118)",
    ],
    "February": [
        "Angel Nebula (NGC 2170)",
        "Cone Nebula and Christmas Tree Cluster (NGC 2264)",
        "Jellyfish Nebula (IC 443 / Sharpless 248)",
        "M35 Open Cluster (NGC 2168)",
        "M37 Open Cluster (NGC 2099)",
        "M78 Reflection Nebula (NGC 2068)",
        "NGC 2158",
        "Rosette Nebula (Caldwell 49) - bring your H-Alpha filter to this one!",
        "Thor's Helmet (NGC 2359)",
    ],
    "March": [
        "Eskimo Nebula / Clown-Faced Nebula / Lion Nebula (NGC 2392 / Caldwell 39)",
        "M46 Open Cluster (NGC 2437)",
        "M47 Open Cluster (NGC 2422)",
        "M67 Open Cluster (NGC 2682)",
        "Medusa Nebula (Abell 21 / Sharpless 2-274)",
        "NGC 2403 Spiral Galaxy (Caldwell 7)",
        "NGC 2903 Barred Spiral Galaxy",
    ],
    "April": [
        "Bode's Galaxy (M81)",
        "Cigar Galaxy (M82) - Bode's and Cigar galaxies are close, so we often photograph them together as one shot.",
        "Leo Triplet in the Leo constellation (M65 / NGC 3623, M66 / NGC 3627, Hamburger Galaxy / NGC 3628)",
        "Hickson 44 Galaxy Group (HCG 44 - NGC 3185, NGC 3187, NGC 3190, NGC 3193)",
        "Little Pinwheel Galaxy (NGC 3184)",
        "M108 Barred Spiral Galaxy (NGC 3556)",
        "M95 Barred Spiral Galaxy (NGC 3351)",
        "M96 Intermediate Spiral Galaxy (NGC 3368)",
        "NGC 3718 Galaxy (Arp 214)",
        "NGC 3729 Barred Spiral Galaxy",
        "Owl Nebula (M97 / NGC 3587)",
    ],
    "May": [
        "Hockey Stick / Crowbar Galaxies (NGC 4656 and NGC 4657)",
        "M100 Galaxy Grand Design Intermediate Spiral Galaxy (NGC 4321)",
        "M106",
        "Intermediate Spiral Galaxy Galaxy (NGC 4258)",
        "M109 Barred Spiral Galaxy (NGC 3992)",
        "M94 Spiral Galaxy (NGC 4736)",
        "Markarian's Chain (M84 / NGC 4374, M86 / NGC 4406, NGC 4477, NGC 4473, NGC 4461, NGC 4458, NGC 4438, NGC 4435)",
        "NGC 4312 Edge-On Unbarred Spiral Galaxy",
        "NGC 4725 Intermediate Barred Spiral Galaxy",
        "Needle Galaxy (NGC 4565 / Caldwell 38)",
        "Silver Needle Galaxy (NGC 4244 / Caldwell 26)",
        "Sombrero Galaxy (M104 / NGC 4594)",
        "Whale Galaxy (NGC 4631 / Caldwell 32)",
    ],
    "June": [
        "Black Eye Galaxy / Sleeping Beauty Galaxy / Evil Eye Galaxy (M64 / NGC 4826)",
        "M3 Globular Cluster (NGC 5272)",
        "M5 Globular Cluster (NGC 5904)",
        "Pinwheel Galaxy (M101 / NGC 5457)",
        "Splinter Galaxy / Knife Edge Galaxy (NGC 5907)",
        "Sunflower Galaxy (M63 / NGC 5055)",
        "Whirlpool Galaxy (M51a / NGC 5194)",
    ],
    "July": [
        "Cat's Eye Nebula (NGC 6543 / Caldwell 6)",
        "Hercules Globular Cluster (M13 / NGC 6205)",
        "Lagoon Nebula (M8 / NGC 6523 / Sharpless 25)",
        "M12 Globular Cluster (NGC 6218)",
        "Trifid Nebula (M20 / NGC 6514)",
    ],
    "August": [
        "Barnard's Galaxy (NGC 6822 / IC 4895 / Caldwell 57)",
        "Dumbbell Nebula / Apple Core Nebula (M27 / NGC 6853)",
        "Crescent Nebula (NGC 6888 / Caldwell 27 / Sharpless 105)",
        "Eagle Nebula (M16 / NGC 6611) - the famous Pillars of Creation are inside this nebula!",
        "M22 Globular Cluster (NGC 6656)",
        "Omega / Swan Nebula (M17 / NGC 6618)",
        "Ring Nebula (M57 / NGC 6720)",
        "Wild Duck Cluster (M11 / NGC 6705)",
    ],
    "September": [
        "Elephant's Trunk Nebula (IC 1396)",
        "Fetus Nebula (NGC 7008)",
        "Fireworks Galaxy (NGC 6946)",
        "Iris Nebula (NGC 7023 / Caldwell 4)",
        "M15 Globular Cluster (NGC 7078)",
        "M2 Globular Cluster (NGC 7089)",
        "NGC 6939 Cluster",
        "North America Nebula (NGC 7000 / Caldwell 20)",
        "Pelican Nebula (IC 5070 and IC 5067)",
        "Veil Nebula",
    ],
    "October": [
        "Blue Snowball Nebula (NGC 7662 / Caldwell 22)",
        "Bubble Nebula (NGC 7635 / Caldwell 11) • Bubble Nebula Wallpaper",
        "Cave Nebula (Caldwell 9 / Sharpless 155)",
        "Cocoon Nebula (IC 5146 / Caldwell 19 / Sh 2-125 / Barnard 168)",
        "Deer Lick Galaxy Group (NGC 7331 Group)",
        "Helix Nebula (NGC 7293 or Caldwell 63)",
        "Stephan's Quintet (NGC 7317, NGC 7318a, NGC 7318b, NGC 7319, NGC 7320c)",
        "Wizard Nebula (NGC 7380)",
    ],
    "November": [
        "Andromeda Galaxy (M31 / NGC 224) - the easiest galaxy to photograph and the most popular one! Its apparent width size is six times the Moon's.",
        "Owl Cluster (NGC 457)",
        "Pacman Nebula (NGC 281)",
        "Phantom Galaxy (M74 / NGC 628)",
        "Sculptor Galaxy / Silver Coin (NGC 253)",
        "Skull Nebula (NGC 246 / Caldwell 56)",
        "Triangulum Galaxy (M33 / NGC 598)",
    ],
    "December": [
        "Amatha Galaxy (NGC 925)",
        "Double Cluster (also known as Caldwell 14 - open clusters NGC 869 and NGC 884)",
        "Heart Nebula (IC 1805)",
        "Little Dumbbell Nebula (M76, NGC 650 / 651)",
        "Nautilus Galaxy (NGC 772)",
        "Silver Sliver / Outer Limits Galaxy (NGC 891)",
        "Soul Nebula (Sharpless 2-199)",
        "Squid Galaxy (M77 / NGC 1068)",
    ],
}


class AstrophotonsRecommendationToolArgs(BaseModel):
    month: str = Field(
        description="The month to recommend targets for. Must be one of the following: January, February, March, April, May, June, July, August, September, October, November, December."
    )


class AstrophotonsRecommendationTool(BaseTool):
    name: str = "astrophotons_recommendation"
    description: str = (
        """
""".strip()
    )

    args_schema: type[AstrophotonsRecommendationToolArgs] = (
        AstrophotonsRecommendationToolArgs
    )

    def _run(self, month: str) -> str:
        recs = "\n".join(astrophotons_recommendations[month])
        return f"""
{month} Astrophotography Targets:

{recs}

Source: <https://astrophotons.com/astrophotography-targets-by-month>
"""
