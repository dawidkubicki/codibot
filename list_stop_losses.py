stop_losses = [0.4, 0.5]
stop_counts = [f"{stop}_{idx}" for idx, stop in enumerate(stop_losses)]
print(stop_counts)
