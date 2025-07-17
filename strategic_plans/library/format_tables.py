def format_coef(coef, p):
    if p >= 0.05:
        coef = str(coef)
    if p < 0.05 and p > 0.01:
        coef = str(coef) + "*"
    if p < 0.01 and p > 0.001:
        coef = str(coef) + "**"
    if p < 0.001:
        coef = str(coef) + "***"
    if (p >= 0.05) & (p < 0.10):
        coef = str(coef) + "†"
    return coef


def format_se(se, round=2):
    formatted_se = "(" + str(se.round(round)) + ")"
    return formatted_se
