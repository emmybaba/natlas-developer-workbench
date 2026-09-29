from runtime.gradio import GradioRuntime


runtime = GradioRuntime(
    temperature=0.2,
    max_tokens=100,
)


response = runtime.generate(
    "In one sentence, explain why developer SDKs are useful for AI models."
)


print("\nN-ATLaS response:")
print(response)