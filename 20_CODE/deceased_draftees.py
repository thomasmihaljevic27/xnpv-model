"""
deceased_draftees.py -- drafted players who died before reaching the NHL, left out of every fit (v1.0).

DECIDED (Thomas, 2026-10-15): "Exclude drafted players who died before reaching the NHL from every fit (the draft
pick curve, the star values and the prospect model) ... and list them in the document as excluded with the reason."
His reason: such a player "obviously did not make the NHL through no fault of his own". The NHL also compensates a
club whose unsigned draftee dies (the 2008 rule named after Cherepanov), so the club is not left with nothing.

THE RULE: drafted 2007-2017 (the fit drafts), never reached the NHL under the model's line (pick_curve route "never
played"), and died before his club control would have ended (pick_curve window_end). A player who died after his
control ended (Adam Comrie, 2008 #80 Florida, died August 2020; control ended 2018) stays in: his death did not cut
his chance short.

THE LIST, from Wikipedia's "List of ice hockey players who died during their careers" (read 2026-10-15), each
matched by draft year and overall pick to draft_pick_linkage.csv. Rodion Amirov (2020 #15 Toronto, died 2023-08-14)
is outside the fit drafts and was never traded; the rule covers him if the fit drafts ever extend to 2020.

pick_curve.py marks these players (column excluded_deceased) and leaves them out of every star value; every script
that refits on pick_curve_players.csv drops the marked rows.
"""

# (draft year, overall pick): (name, date of death)
DECEASED = {
    (2007, 17): ("Alexei Cherepanov", "2008-10-13"),
    (2007, 143): ("Mickey Renaud", "2008-02-18"),
    (2007, 208): ("Bryan Rufenach", "2012-06-04"),
    (2008, 89): ("Scott Winkler", "2013-06-12"),
    (2010, 181): ("Kristians Pelss", "2013-06-11"),
    (2011, 166): ("Daniil Sobchenko", "2011-09-07"),
}


def is_deceased(draft_year, pick):
    return (int(draft_year), int(pick)) in DECEASED
