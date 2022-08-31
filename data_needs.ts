// ML Data Set

interface MLDataset {
 matchId: bigint
 heroId: number // in order of selecting skills,
 heroSlot: number
 skillIds: number[] // in order of being picked, unpicked skills would be last
 pickNumber: number[] // corresponding pick number for each skill (this could be calculated based on heroSlot)
 scepter: boolean[] // boolean flag whether the ags was upgraded
 shard: boolean[] // boolean flag whether the ags was upgraded
 win: boolean // whether player won
 dire: boolean // whether the player was dire again could be calculated by heroSlot but makes it easy
 gold: number // player stats normalized to match length
 assists: number // see above
 damage: number // see above
 deaths: number // see above
 xp: number
}

interface SkillStats {
    skillId: number
    pickStats: {
        mean: number // mean pick
        median: number // median pick
        interval25: number // 25% certainty min pick
        interval75: number // 75% confidence max pick
        std: number // standard deviation of pick
        winPick: number // pick where win rate turns positive
    },
    survivalRate: number[] // 40 length array providing percentage of matches where the pick survied the pick (i.e. index number),
    winStats: {
        win: number // overall win percentage
        winRate: number[] // 40 length array providing win rate of matches depending on where picked, calculate from rounds and interpolate using power law
    }
    gold: number // player stats normalized to match length
    assists: number // see above
    damage: number // see above
    deaths: number // see above
    xp: number // see above
}
