def calculate_interest(parameters: dict, player=None, speak=None) -> str:
    principal = float(parameters.get("principal", 0))
    rate = float(parameters.get("rate", 0))
    time = float(parameters.get("time", 0))
    amount = principal * (1 + rate / 100) ** time
    interest = amount - principal
    return f"Principal: {principal}, Rate: {rate}%, Time: {time} years. Total Amount: {amount:.2f}, Interest Earned: {interest:.2f}."