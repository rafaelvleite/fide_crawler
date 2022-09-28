#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Sep 27 22:54:45 2022

@author: hack-rafa
"""

def ratingPerformance(numberOfGames, points, opponentsAverageRating, ratingSum, totalWins, totalLosses):    
    if numberOfGames == 8:
        if points == 0:
            return opponentsAverageRating - 800
        if points == 0.5:
            return opponentsAverageRating - 444
        if points == 1:
            return opponentsAverageRating - 322
        if points == 1.5:
            return opponentsAverageRating - 251
        if points == 2:
            return opponentsAverageRating - 193
        if points == 2.5:
            return opponentsAverageRating - 141
        if points == 3:
            return opponentsAverageRating - 95
        if points == 3.5:
            return opponentsAverageRating - 43
        if points == 4:
            return opponentsAverageRating
        if points == 4.5:
            return opponentsAverageRating + 43
        if points == 5:
            return opponentsAverageRating + 95
        if points == 5.5:
            return opponentsAverageRating + 141
        if points == 6:
            return opponentsAverageRating + 193
        if points == 6.5:
            return opponentsAverageRating + 251
        if points == 7:
            return opponentsAverageRating + 322
        if points == 7.5:
            return opponentsAverageRating + 444
        if points == 8:
            return opponentsAverageRating + 800
    
    elif numberOfGames == 9:
        if points == 0:
            return opponentsAverageRating - 800
        if points == 0.5:
            return opponentsAverageRating - 444
        if points == 1:
            return opponentsAverageRating - 351
        if points == 1.5:
            return opponentsAverageRating - 273
        if points == 2:
            return opponentsAverageRating - 220
        if points == 2.5:
            return opponentsAverageRating - 166
        if points == 3:
            return opponentsAverageRating - 125
        if points == 3.5:
            return opponentsAverageRating - 80
        if points == 4:
            return opponentsAverageRating - 43
        if points == 4.5:
            return opponentsAverageRating
        if points == 5:
            return opponentsAverageRating + 43
        if points == 5.5:
            return opponentsAverageRating + 80
        if points == 6:
            return opponentsAverageRating + 125
        if points == 6.5:
            return opponentsAverageRating + 166
        if points == 7:
            return opponentsAverageRating + 220
        if points == 7.5:
            return opponentsAverageRating + 273
        if points == 8:
            return opponentsAverageRating + 351
        if points == 8.5:
            return opponentsAverageRating + 444
        if points == 9:
            return opponentsAverageRating + 800
        
    elif numberOfGames == 10:
        if points == 0:
            return opponentsAverageRating - 800
        if points == 0.5:
            return opponentsAverageRating - 470
        if points == 1:
            return opponentsAverageRating - 366
        if points == 1.5:
            return opponentsAverageRating - 296
        if points == 2:
            return opponentsAverageRating - 240
        if points == 2.5:
            return opponentsAverageRating - 193
        if points == 3:
            return opponentsAverageRating - 149
        if points == 3.5:
            return opponentsAverageRating - 110
        if points == 4:
            return opponentsAverageRating - 72
        if points == 4.5:
            return opponentsAverageRating - 36
        if points == 5:
            return opponentsAverageRating
        if points == 5.5:
            return opponentsAverageRating + 36
        if points == 6:
            return opponentsAverageRating + 72
        if points == 6.5:
            return opponentsAverageRating + 110
        if points == 7:
            return opponentsAverageRating + 149
        if points == 7.5:
            return opponentsAverageRating + 193
        if points == 8:
            return opponentsAverageRating + 240
        if points == 8.5:
            return opponentsAverageRating + 296
        if points == 9:
            return opponentsAverageRating + 366
        if points == 9.5:
            return opponentsAverageRating + 470
        if points == 10:
            return opponentsAverageRating + 800
    
    elif numberOfGames == 11:
        if points == 0:
            return opponentsAverageRating - 800
        if points == 0.5:
            return opponentsAverageRating - 470
        if points == 1:
            return opponentsAverageRating - 383
        if points == 1.5:
            return opponentsAverageRating - 309
        if points == 2:
            return opponentsAverageRating - 262
        if points == 2.5:
            return opponentsAverageRating - 211
        if points == 3:
            return opponentsAverageRating - 175
        if points == 3.5:
            return opponentsAverageRating - 133
        if points == 4:
            return opponentsAverageRating - 102
        if points == 4.5:
            return opponentsAverageRating - 65
        if points == 5:
            return opponentsAverageRating - 36
        if points == 5.5:
            return opponentsAverageRating
        if points == 6:
            return opponentsAverageRating + 36
        if points == 6.5:
            return opponentsAverageRating + 65
        if points == 7:
            return opponentsAverageRating + 102
        if points == 7.5:
            return opponentsAverageRating + 133
        if points == 8:
            return opponentsAverageRating + 175
        if points == 8.5:
            return opponentsAverageRating + 211
        if points == 9:
            return opponentsAverageRating + 262
        if points == 9.5:
            return opponentsAverageRating + 309
        if points == 10:
            return opponentsAverageRating + 383
        if points == 10.5:
            return opponentsAverageRating + 470
        if points == 11:
            return opponentsAverageRating + 800
    else:
        return round((ratingSum + 400*(totalWins - totalLosses))/numberOfGames)