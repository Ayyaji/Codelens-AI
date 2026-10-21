/**
 * Fixtures for the JD, test, auth, My Space, and teacher routes.
 * Shapes match rag_core/schemas.py. See frontend/API_CONTRACT.md.
 * POST /ask is mocked only when VITE_USE_MOCKS or the `ask` name is on.
 */

import { rememberAttempt, rememberJd } from "./store";

export {
  DEMO_ACCOUNTS,
  mockActivity,
  mockApproveKb,
  mockAsk,
  mockEditKb,
  mockHistory,
  mockLogin,
  mockMe,
  mockMyChat,
  mockMyChats,
  mockOverview,
  mockPendingKb,
  mockPersona,
  mockRegister,
  mockRejectKb,
  mockResetStudent,
  mockSetDisabled,
  mockStudent,
  mockStudentChat,
  mockStudentChats,
  mockStudents,
} from "./store";

const wait = (ms = 280) => new Promise((resolve) => setTimeout(resolve, ms));

export async function mockUpload({ token, filename } = {}) {
  await wait();
  if (!token) return { jd_id: "jd_mock_8f3a1c" };
  return rememberJd({ token, filename });
}

export async function mockAnalysis() {
  await wait();
  return {
    skills: [
      {
        name: "Python",
        level: "intermediate",
        explanation: "The service code is Python. You will read traces, write small scripts, and explain what a function does.",
      },
      {
        name: "SQL",
        level: "intermediate",
        explanation: "The role queries a relational database. Joins, filters, and indexes show up in the day-to-day work.",
      },
      {
        name: "REST APIs",
        level: "beginner",
        explanation: "You will call and describe HTTP endpoints: status codes, JSON bodies, and what a client sends.",
      },
      {
        name: "Testing",
        level: "advanced",
        explanation: "The posting asks for tests around the code you change, including a failing case you can explain.",
      },
      {
        name: "Git",
        level: "beginner",
        explanation: "You will branch, commit, and open a review. The interview checks that you can narrate a small change.",
      },
    ],
    roadmap: [
      {
        order: 1,
        skill: "Python",
        goal: "Read a traceback and fix a small function",
        practice: "Write a function that parses a line of integers and handles an empty line",
      },
      {
        order: 2,
        skill: "SQL",
        goal: "Filter and join two tables",
        practice: "Write three joins against a students and enrolments example",
      },
      {
        order: 3,
        skill: "REST APIs",
        goal: "Describe a request and its status code",
        practice: "Sketch GET and POST for a jobs resource, including one error response",
      },
      {
        order: 4,
        skill: "Testing",
        goal: "Name the case a test is protecting",
        practice: "Add one passing and one failing assertion around the integer parser",
      },
      {
        order: 5,
        skill: "Git",
        goal: "Explain a commit in one sentence",
        practice: "Commit the parser and the test as two separate changes",
      },
    ],
  };
}

export async function mockGenerate() {
  await wait();
  return {
    jd_id: "jd_mock_8f3a1c",
    questions: [
      {
        id: "q1",
        type: "mcq",
        skill: "SQL",
        prompt: "Which clause keeps rows after a join has already combined them?",
        options: ["WHERE", "ORDER BY", "GROUP BY", "LIMIT"],
      },
      {
        id: "q2",
        type: "mcq",
        skill: "Python",
        prompt: "A function returns None and the caller subscripts it. Which exception is that?",
        options: ["TypeError", "NameError", "IndexError", "SyntaxError"],
      },
      {
        id: "q3",
        type: "mcq",
        skill: "REST APIs",
        prompt: "A client sends a body the server cannot parse. Which status fits best?",
        options: ["200", "201", "400", "500"],
      },
      {
        id: "q4",
        type: "mcq",
        skill: "Testing",
        prompt: "What does a unit test protect when a later edit changes the function?",
        options: [
          "The exact lines of the implementation",
          "A behaviour you can name in the assertion",
          "The time the suite takes to start",
          "The name of the file",
        ],
      },
      {
        id: "c1",
        type: "coding",
        skill: "Python",
        prompt: "Read one integer from stdin and print its double. A blank line should print 0.",
        language: "python",
        starter_code: "raw = input().strip()\nif not raw:\n    print(0)\nelse:\n    print(int(raw) * 2)\n",
        sample_input: "2",
        sample_output: "4",
      },
      {
        id: "c2",
        type: "coding",
        skill: "SQL",
        prompt: "You cannot run SQL here. Write a Python program that reads `table rows` as integers on one line and prints how many are greater than 10.",
        language: "python",
        starter_code: "nums = [int(part) for part in input().split()]\nprint(sum(1 for n in nums if n > 10))\n",
        sample_input: "4 12 10 18",
        sample_output: "2",
      },
    ],
  };
}

export async function mockSubmit({ token, jdId } = {}) {
  await wait(360);
  const result = {
    score: 66.7,
    weak_topics: ["SQL", "Testing"],
    guidance: {
      directive: "hint",
      message:
        "You have run into SQL before. Take only this nudge and try again before reading a full solution. The join was filtered with the wrong clause, so the extra rows stayed in the result.",
      next_steps: [
        "SQL: Write three joins against a students and enrolments example",
        "Testing: Add one passing and one failing assertion around the integer parser",
      ],
      mistake_patterns: ["concept_gap:SQL", "wrong_output:Testing"],
    },
  };
  if (token) rememberAttempt({ token, jdId, result });
  return result;
}

export async function mockRun({ code, language }) {
  await wait(180);
  const lang = (language || "").trim().toLowerCase();
  if (!["python", "py", "python3"].includes(lang)) {
    return { stdout: "", stderr: `Unsupported language: ${language}. Only python can be run here.\n` };
  }
  if (!code || !String(code).trim()) {
    return { stdout: "", stderr: "No code was provided.\n" };
  }
  return { stdout: "4\n", stderr: "" };
}
