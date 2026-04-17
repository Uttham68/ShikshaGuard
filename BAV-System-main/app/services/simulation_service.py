def simulate_impact(school: dict, proposal: dict):
    total_students = float(school.get("total_students", 0))
    total_tch = max(float(school.get("total_tch", 1)), 1)
    current_classrooms = max(float(school.get("classrooms_total", 1)), 1)

    new_classrooms = current_classrooms + proposal.get("classrooms_requested", 0)

    # Current metrics
    current_ptr = total_students / total_tch
    current_spc = total_students / current_classrooms

    # New metrics
    new_ptr = total_students / total_tch  # teachers unchanged
    new_spc = total_students / new_classrooms

    # Risk reduction logic
    reduction = 0

    if current_spc > 40:
        reduction += min((current_spc - new_spc) * 2, 40)

    if current_ptr > 35:
        reduction += min((current_ptr - new_ptr) * 2, 30)

    reduction = round(min(reduction, 100), 2)

    # Impact category
    if reduction > 50:
        impact = "High Improvement"
    elif reduction > 20:
        impact = "Moderate Improvement"
    else:
        impact = "Low Improvement"

    return {
        "current": {
            "ptr": round(current_ptr, 2),
            "students_per_classroom": round(current_spc, 2),
        },
        "after": {
            "ptr": round(new_ptr, 2),
            "students_per_classroom": round(new_spc, 2),
        },
        "risk_reduction": reduction,
        "impact": impact,
    }