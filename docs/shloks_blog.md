OpenPoke: Recreating Poke's Architecture
Reverse-engineering the Poke assistant and open-sourcing a working prototype of its multi-agent architecture.
September 22, 2025
A few days back, the Interaction Company of California launched Poke, an assistant chatbot that lives inside iMessage. The launch captured the timeline's attention through a storm of viral elements—the launch video, the absolutely unhinged onboarding (Poke haggles with you over its own pricing), and the eerie, wtf?? feeling of watching an AI rifle through your email inbox before weaponizing that knowledge to roast you.

Poke haggling with a new user during iMessage onboarding

But beyond these theatrics, Poke is special because it's the first everyday consumer AI product since ChatGPT that people find genuinely, consistently useful. Setting reminders, surfacing important emails, automating tasks, scheduling meetings, bridging external tools like Linear and Notion—it all just works, with zero friction. And unlike the sanitized, servile tone of most AI chatbots, it does so with actual personality.

Screenshots showing Poke acting as a proactive personal assistant

Since the launch, I've been obsessively using Poke not just for its intended purpose but also to dissect what makes it so compelling. Then last week, someone managed to exfiltrate its system prompts (hilariously, by asking Poke to email them). This finally gave me a window into how it works: a sophisticated multi-agent architecture with orchestration, agents spawned on demand, multiple integrated tools, and persistent memory.

I spent the last three days replicating Poke's architecture. I got pretty far and now have a working prototype, which I'm releasing as OpenPoke. In this post, I'll first deconstruct OpenPoke's architecture, then share insights on critical design decisions and what builders can steal for their own AI applications.

shlokkhemani avatar
shlokkhemani/OpenPoke
openpoke
Open source implementation of Poke

View on GitHub
Note:

If you haven't tried Poke yet, do it before reading further. Everything will click better and you'll glimpse an inevitable future.
This analysis is based on the leaked system prompts and my own usage of Poke. While I'm confident about the architecture high level, the specifics might be off. The team has also likely made changes since the prompt leak.
What is OpenPoke?
OpenPoke is a stripped-down implementation of Poke that runs locally and captures its core architecture. It handles two fundamental capabilities: email management (searching your inbox, drafting replies, surfacing important incoming messages) and persistent reminders/automations (like "summarize my emails every night at 9pm").

What is OpenPoke
What's missing is Poke's full arsenal—the integrations with Linear and Notion, calendar orchestration, web search, and the personality layer that makes it feel genuinely alive. It has other limitations that I discuss later in the article.

Architecture Overview
Most agentic systems today process request through iterative tool calls in a single thread. OpenPoke instead deploys an orchestrated multi-agent system where an Interaction Agent acts as the conductor, managing a dynamic swarm of Execution Agents—specialized workers spawned on-demand for specific tasks.

High-level diagram of OpenPoke's orchestrated architecture

Interaction Agent
The Interaction Agent is your sole interface—it talks to you, maintains context, and delegates work. When it receives a request, it checks its roster of existing Execution Agents to see if any can handle the task. If not, it spawns new ones. These Execution Agents operate independently in parallel. When they complete their work, the Interaction Agent synthesizes their outputs into a coherent reply.

Let's see this in action. You message: "Can you ask Alice and Bob if they're free for lunch tomorrow?" The Interaction Agent identifies two distinct email tasks. It checks its roster—no existing agents for either person. So it spawns two new Execution Agents simultaneously: "Email to Alice" and "Email to Bob." Both start working in parallel, each crafting drafts independently. When both finish, the Interaction Agent weaves their separate outputs into a single response: "I've drafted lunch invitations for both Alice and Bob for tomorrow. Send both?" Once you confirm, the same Execution Agents handle the sending, again working in parallel.

The Interaction Agent spawning multiple email-writing agents in parallel
Now you follow up an hour later: "Did Alice reply yet?" The Interaction Agent checks its roster and finds the "Email to Alice" agent still alive. It routes your question to this existing agent, which already holds the entire Alice email thread in its own memory (more on this in a bit). The agent checks for new replies and responds accordingly.

Apart from orchestration, the Interaction Agent is responsible for personality and UX. It's prompted to be sharp, witty, direct, and explicitly instructed "don't act like other sycophantic chatbots." It also curates what reaches you: when background workers or Execution Agents produce outputs, the Interaction Agent evaluates whether that information is redundant or irrelevant to the current conversation. If so, it invokes a special "wait" tool, silently discarding the message rather than cluttering the chat with noise.


The draft tool
The Interaction Agent also has access to a draft tool for displaying email drafts. Unlike a normal assistant message (which the Interaction Agent would weave into a conversational reply), draft content is inserted verbatim into the user’s chat and is not stylized.

Execution Agents
Each Execution Agent is a specialized LLM instance with its own system prompt, conversation history, and toolset. These agents own entire threads of work—the "Email to Alice" agent doesn't just create a single draft but becomes the permanent owner of all Alice-related email interactions.

When the Interaction Agent spawns an Execution Agent, it provides clear, actionable instructions: “Email Alice to ask if she’s free for lunch tomorrow. Bob’s also coming.” From there, the Execution Agent enters an independent reasoning loop, calling tools and iterating until the task reaches completion. In our lunch scenario, it might begin by searching contacts for Alice’s email address, then craft a thoughtful invitation draft.

Upon completion, the agent delivers a status report: “Found Alice at alice@piedpiper.com. Draft ready: [content]. Awaiting your confirmation to send.”

While most agentic systems treat sub-agents as ephemeral—spin up, execute, terminate—OpenPoke’s Execution Agents persist indefinitely. Each agent maintains a complete log of its requests, tool calls, and replies. Hours later, when you ask “Did Alice reply?” the same agent that crafted the original invitation springs back to life, context intact. It checks for new messages from Alice and responds accordingly.

Tools
Tools are made available to Execution Agents to complete their assigned tasks. OpenPoke has two categories:

Gmail tools: creating drafts, sending emails, replying to threads, forwarding messages, and looking up contacts (implemented via Composio)
Trigger tools: Creating, updating, and listing automated reminders and scheduled tasks
Each tool performs a single atomic operation. Since Execution Agents operate in LLM loops, they chain these operations together to handle complex workflows.

Tasks
Tasks are exposed as tools to Execution Agents but handle more complex operations that simple tools might struggle with. While tools perform atomic actions, tasks orchestrate multiple steps.

OpenPoke implements a "search email" task that when given a query fans out multiple searches across different time periods and related keywords, then aggregates and cleans the results. This prevents agents from drowning in raw email data while ensuring comprehensive coverage.

Poke uses tasks to define MCP integrations with external services like Notion and Linear. This elegantly solves the "tool call bloat" problem—rather than exposing every possible Notion API endpoint upfront, an Execution Agent simply determines that Notion is relevant to its task, then delegates the specifics to the Notion Task.

OpenPoke doesn't support MCP yet.

Triggers
Triggers are OpenPoke's reminder system—scheduled tasks that execute at specific times or intervals. When you say "Remind me to meditate every morning" or "Email me a summary of today's messages every night at 9pm," you're creating triggers.

Each trigger belongs to the Execution Agent that created it. This scoping prevents chaos—the "Email to Alice" agent can't accidentally modify triggers from the "Weekly Report" agent. Triggers support both one-time events and recurring schedules with natural language patterns like "every weekday" or "first Monday of the month."

Triggers live in an SQL database. A scheduler runs as a background service, checking every minute for due triggers. When one fires, it reactivates the original Execution Agent that created it, providing the trigger context as input. That agent then executes in the background—sending emails, generating summaries, checking for updates—and routes its output back to the Interaction Agent.

OpenPoke creating and firing a scheduled reminder
Email Monitoring
Beyond responding to direct requests, OpenPoke continuoulsy monitors your inbox. Every minute, a background worker fetches new emails and evaluates them through an LLM classifier—analyzing for urgency, required actions, OTP codes, and sender importance.

OpenPoke background monitor highlighting a high-priority email reminder
When an email crosses the importance threshold, the monitor sends it to the Interaction Agent, which weaves it naturally into your conversation: "By the way, Alice just confirmed lunch."

The email monitor functions like a specialized Execution Agent with predefined instructions—one that runs continuously in the background rather than being summoned by the Interaction Agent. It maintains its own memory of processed messages to avoid duplicates.

Memory
OpenPoke employs a multi-tiered memory architecture: immediate recall of recent events, compressed representations of older ones, and on-demand access to external records.

Conversation Memory
The Interaction Agent starts with complete access to your entire conversation history—every message, request, and response. But just raw history creates a scaling problem: as conversations grow, the context window gets bloats. The LLM doesn’t need to remember that you asked about the weather three weeks ago when you’re scheduling today’s meetings.

OpenPoke solves this through summarization. Once your conversation reaches 100 messages (a configurable threshold), it triggers a structured summarization pass with temporal anchoring and semantic preservation. When you asked OpenPoke to “email John about the proposal” three days ago, the compressed memory preserves this as “Sent proposal email to John on September 18, 2025.” The system retains what matters: your preferences, active tasks, relationship context—while discarding conversational noise.

This compression runs continuously in cascading layers. Recent interactions remain at full fidelity while older summaries undergo progressive compression, creating a natural decay curve.

Agent Memory
Each Execution Agent maintains its own persistent memory—a complete log of every action it's taken, every tool it's called, and every result it's received.

Remember our lunch invitation example? The "Email to Alice" agent sends the initial invitation on Monday. Alice replies Wednesday accepting but suggesting a different restaurant. A month later, she follows up: "Hey, regarding that lunch we discussed—want to do the same thing next week?"

When you forward this to OpenPoke asking "What lunch is Alice talking about?", the Interaction Agent uses the same "Email to Alice" agent from a month ago. That agent still has the entire context: the original invitation, the restaurant discussion, who else was invited. It immediately understands Alice's reference and can craft an informed reply: "She's referring to the lunch from September 20th at Chez Philippe with you, her, and Bob. Should I confirm the same setup for next week?"

While the Interaction Agent’s conversation memory undergoes compression—reducing “Handled Alice lunch coordination in September” to save context window space—the Execution Agents preserve their complete operational histories. The “Email to Alice” agent remembers everything: the exact times proposed, dietary restrictions mentioned, the jokes exchanged about the restaurant choice.

Email as External Memory
Treating email access as memory infrastructure might seem unconventional, but it’s OpenPoke’s most powerful memory feature.

Your inbox is a living archive of your life, complete with both present and temporal knowledge. Flight confirmations show not just where you're going, but your travel patterns over years. Emails exchanged show changing relationship dynamics, like the colleague who became a confidant. Purchase histories document life transitions—from apartment essentials to baby supplies.

When you ask OpenPoke "What was that restaurant I loved in Tokyo?", it finds the reservation confirmation from two years ago. When you wonder "How long have I been working with this vendor?", it traces the email thread back to the first inquiry. The temporal dimension transforms isolated facts into patterns and insights that even you might not consciously remember.

Without email access, an AI assistant only knows what happens during your conversations with it. And because most AI is reactive rather than proactive, it doesn't actively probe you—"who are your friends? what did you eat today? where are you traveling next month?"—nor would you necessarily want it to.

External data sources like email provide passive context accumulation. Your assistant understands your life without requiring manual briefings about every relationship, project, or preference. Today it’s Gmail. Tomorrow it could be your iMessage threads, Slack conversations, or calendar entries. Each integration deepens understanding without adding friction.

How it all fits together
Sequence diagram showing how the Interaction Agent, Execution Agents, and monitors collaborateopenpoke_architecture.jpg

Where OpenPoke Falls Short
While OpenPoke captures Poke’s core architecture, several critical aspects remain unimplemented or unoptimized—gaps that helped me appreciate just how much engineering goes into making a consumer AI product feel magical.

Execution Agent Overload
Currently, the entire roster of Execution Agents is passed to the Interaction Agent with every request. After days of use, you might have hundreds of specialized agents—"Email to Alice," "Q3 Budget Analysis," "Tokyo Restaurant Search"—all competing for the Interaction Agent's attention. This creates a relevance problem. The naive solution would be implementing semantic search over agent descriptions. Other options include archiving dormant agents, clustering related ones, or maintaining a hot cache of recently active agents.

The Personality Gap
Poke's personality and UX is art. How it breaks lengthy responses into rapid-fire messages mimicking human texting. When it chooses brevity versus detail. The humor that feels natural, not forced. OpenPoke attempts basic personality through prompting, but matching Poke’s distinctive voice requires either exhaustive prompt engineering across thousands of interactions or a fine-tuned model.

Economics
OpenPoke defaults to Claude Sonnet 4 for every LLM call, and costs compound quickly. A single complex request might trigger the Interaction Agent, spawn three Execution Agents, each making multiple tool calls with their own LLM loops—easily 10-15 calls per user message. Poke likely optimizes these costs (the system prompt mentions trigger creation using a smaller model). The leaked prompt also mentions $50 per user monthly in actual costs.

Response Latency
OpenPoke feels sluggish compared to Poke's snappy responses. I've put zero effort into optimizing for latency. Poke has likely had months of real usage data to identify bottlenecks and optimize the critical paths.

Takeaways for Builders
Separate Personality from Execution
Most AI agents conflate personality with task completion—a single agent trying to be charming while also managing complex workflows. Poke separates these completely. The Interaction Agent owns the entire personality layer while Execution Agents are pure task machines with zero personality instructions. This separation also lets you iterate on user experience without touching core functionality, and optimize execution without breaking the voice that users love.

Embrace Asynchrony
You can give Poke five different tasks and continue chatting while they execute in parallel. Compare this to ChatGPT, Claude, or Cursor—they lock you into sequential request-response cycles. This is fundamentally better, more natural.

Layer Your Memory Systems
Most AI applications rely on single memory approaches—conversation history, RAG, or profile building. Poke uses three: conversation logs and summaries for the main agent, agent logs for operational memory, and email as external truth. Each layer serves different purposes and operates at different timescales. Your email knows things about you that you’d never tell an AI assistant.

Build From First Principles
Poke didn’t try to be better ChatGPT. They questioned every assumption. Why have a separate app when iMessage exists on every phone? Why force users into multiple conversation threads when life flows continuously? Why pretend to do everything when excelling at specific things creates more value? They consciously chose not to code or generate images—constraints that let them perfect what mattered.

Personality Is Product
We have intelligence on tap. Make it delightful. AI assistants don’t need to sound like subservient robots. The right personality transforms utility into something users actually want to interact with.

Conclusion
Kudos to the Interaction team for building something genuinely new and beautiful. Reverse-engineering Poke has been more rewarding than I imagined—not just for understanding their specific implementation, but for glimpsing how AI assistants are becoming more sophisticated and woven into our lives.