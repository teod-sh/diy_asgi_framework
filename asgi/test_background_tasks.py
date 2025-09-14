import asyncio
import time
import unittest
from collections import namedtuple
from unittest.mock import AsyncMock

from asgi.background_tasks import (
    BackgroundTasks,
    TaskParams,
    create_task,
    _reset_instance
)


class TestBackgroundTasks(unittest.TestCase):

    def setUp(self):
        _reset_instance()
        self.bg_tasks = BackgroundTasks()

    def tearDown(self):
        _reset_instance()

    def test_init_invalid_parameters(self):
        TestCase = namedtuple('TestCase', ['max_running_tasks', 'error_message'])
        test_cases = [
            TestCase(max_running_tasks="5", error_message="max_running_tasks must be an integer"),
            TestCase(max_running_tasks=-1, error_message="max_running_tasks must be minimum 0"),
            TestCase(max_running_tasks=5.5, error_message="max_running_tasks must be an integer"),
            TestCase(max_running_tasks=None, error_message="max_running_tasks must be an integer"),
        ]

        for case in test_cases:
            with self.subTest(max_running_tasks=case.max_running_tasks):
                with self.assertRaises(AssertionError) as context:
                    BackgroundTasks(max_running_tasks=case.max_running_tasks)
                self.assertEqual(str(context.exception), case.error_message)

    def test_generate_task_id_format(self):
        handler_name = "testhandler"
        task_id = BackgroundTasks._generate_task_id(handler_name)

        parts = task_id.split("_")

        self.assertEqual(parts[0], handler_name)
        self.assertEqual(len(parts), 3)

        timestamp = int(parts[-1])
        current_time = int(time.time())
        self.assertLessEqual(abs(current_time - timestamp), 60)


class TestBackgroundTasksAsync(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        _reset_instance()
        self.bg_tasks = BackgroundTasks(max_running_tasks=2)

    async def asyncTearDown(self):
        _reset_instance()

    async def test_add_tasks(self):
        async def mock_handler(params: TaskParams):
            pass

        tasks = [
            create_task(mock_handler, TaskParams(data="test1")),
            create_task(mock_handler, TaskParams(data="test2")),
        ]

        await self.bg_tasks.add_tasks(tasks)

        self.assertEqual(len(self.bg_tasks._tasks_map), 2)
        self.assertEqual(self.bg_tasks._task_queue.qsize(), 2)

    async def test_add_tasks_server_shutting_down(self):
        async def mock_handler(params: TaskParams):
            pass

        self.bg_tasks._is_server_shutting_down = True
        tasks = [create_task(mock_handler, TaskParams(data="test"))]

        await self.bg_tasks.add_tasks(tasks)

        self.assertEqual(len(self.bg_tasks._tasks_map), 0)
        self.assertEqual(self.bg_tasks._task_queue.qsize(), 0)

    async def test_get_tasks_to_process_empty_queue(self):
        result = await self.bg_tasks._get_tasks_to_process()
        self.assertEqual(result, [])

    async def test_get_tasks_to_process_max_running_reached(self):
        async def mock_handler(params: TaskParams):
            pass

        tasks = [create_task(mock_handler, TaskParams(data="test"))]
        await self.bg_tasks.add_tasks(tasks)
        self.bg_tasks._on_going_tasks = self.bg_tasks.max_running_tasks

        result = await self.bg_tasks._get_tasks_to_process()
        self.assertEqual(result, [])

    async def test_get_tasks_to_process_server_shutting_down(self):
        async def mock_handler(params: TaskParams):
            pass

        tasks = [create_task(mock_handler, TaskParams(data="test"))]
        await self.bg_tasks.add_tasks(tasks)
        self.bg_tasks._is_server_shutting_down = True

        result = await self.bg_tasks._get_tasks_to_process()
        self.assertEqual(result, [])

    async def test_put_back_to_queue_if_allowed_task_not_exists(self):
        not_exist_id = "nonexistent"
        await self.bg_tasks._put_back_to_queue_if_allowed("nonexistent")
        self.assertNotIn(not_exist_id, self.bg_tasks._tasks_map)

    async def test_put_back_to_queue_if_allowed_max_retries_exceeded(self):
        async def mock_handler(params: TaskParams):
            pass

        task = create_task(mock_handler, TaskParams(data="test"), max_retries=2)
        task._attempts = 2  # Set attempts to max retries
        task_id = "test_task_id"
        self.bg_tasks._tasks_map[task_id] = task

        enqueued = await self.bg_tasks._put_back_to_queue_if_allowed(task_id)
        self.assertFalse(enqueued)
        self.assertEqual(self.bg_tasks._task_queue.qsize(), 0)

    async def test_put_back_to_queue_if_allowed_retry(self):
        async def mock_handler(params: TaskParams):
            pass

        task = create_task(mock_handler, TaskParams(data="test"), max_retries=3)
        task_id = "test_task_id"
        self.bg_tasks._tasks_map[task_id] = task

        await self.bg_tasks._put_back_to_queue_if_allowed(task_id)

        self.assertEqual(task.get_attempts(), 2)
        self.assertEqual(self.bg_tasks._task_queue.qsize(), 1)

    async def test_put_back_to_queue_if_allowed_server_shutting_down(self):
        async def mock_handler(params: TaskParams):
            pass

        task = create_task(mock_handler, TaskParams(data="test"))
        task_id = "test_task_id"
        self.bg_tasks._tasks_map[task_id] = task
        self.bg_tasks._is_server_shutting_down = True

        await self.bg_tasks._put_back_to_queue_if_allowed(task_id)
        self.assertEqual(self.bg_tasks._task_queue.qsize(), 0)

    async def test__run_task_success(self):
        mock_handler = AsyncMock()
        task = create_task(mock_handler, TaskParams(data="test"))
        task_id = "test_task_id"
        self.bg_tasks._tasks_map[task_id] = task
        self.bg_tasks._on_going_tasks = 1

        await self.bg_tasks._run_task(task_id)

        mock_handler.assert_called_once_with(task.params)
        self.assertNotIn(task_id, self.bg_tasks._tasks_map)
        self.assertEqual(self.bg_tasks._on_going_tasks, 0)

    async def test__run_task_timeout(self):
        async def slow_handler(params: TaskParams):
            await asyncio.sleep(10)  # Longer than timeout

        task = create_task(slow_handler, TaskParams(data="test"), timeout_after=1)
        task_id = "test_task_id"
        self.bg_tasks._tasks_map[task_id] = task
        self.bg_tasks._on_going_tasks = 1

        await self.bg_tasks._run_task(task_id)

        # Task should be retried (still in map with incremented attempts)
        self.assertIn(task_id, self.bg_tasks._tasks_map)
        self.assertEqual(task.get_attempts(), 2)
        self.assertEqual(self.bg_tasks._on_going_tasks, 0)
        self.assertEqual(self.bg_tasks._task_queue.qsize(), 1)

    async def test__run_task_exception(self):
        async def failing_handler(params: TaskParams):
            raise ValueError("Test error")

        task = create_task(failing_handler, TaskParams(data="test"))
        task_id = "test_task_id"
        self.bg_tasks._tasks_map[task_id] = task
        self.bg_tasks._on_going_tasks = 1

        # Should not raise exception
        await self.bg_tasks._run_task(task_id)

        self.assertEqual(self.bg_tasks._on_going_tasks, 0)
        self.assertNotIn(task_id, self.bg_tasks._tasks_map)

    async def test_run_tasks_normal_flow(self):
        """Test run_tasks under normal conditions"""
        mock_handler = AsyncMock()
        tasks = [
            create_task(mock_handler, TaskParams(data="test1")),
            create_task(mock_handler, TaskParams(data="test2")),
        ]
        await self.bg_tasks.add_tasks(tasks)

        await self.bg_tasks.run_tasks()

        await asyncio.sleep(0.2)
        self.assertEqual(mock_handler.call_count, 2)
        self.assertEqual(self.bg_tasks._on_going_tasks, 0)
        self.assertEqual(self.bg_tasks._task_queue.qsize(), 0)

    async def test_clean_queue(self):
        async def mock_handler(params: TaskParams):
            pass

        tasks = [
            create_task(mock_handler, TaskParams(data="test1")),
            create_task(mock_handler, TaskParams(data="test2")),
        ]
        await self.bg_tasks.add_tasks(tasks)

        self.assertEqual(self.bg_tasks._task_queue.qsize(), 2)

        await self.bg_tasks._clean_queue()

        self.assertEqual(self.bg_tasks._task_queue.qsize(), 0)

    async def test_shutdown_no_running_tasks(self):
        start_time = time.time()
        await self.bg_tasks.shutdown(timeout=5.0)
        end_time = time.time()

        # Should complete quickly
        self.assertLess(end_time - start_time, 1.0)
        self.assertTrue(self.bg_tasks._is_server_shutting_down)

    async def test_shutdown_with_running_tasks(self):
        async def quick_task(params: TaskParams):
            await asyncio.sleep(0.1)

        task = create_task(quick_task, TaskParams(data="test"))
        task_id = "test_task_id"
        self.bg_tasks._tasks_map[task_id] = task
        self.bg_tasks._on_going_tasks = 1

        asyncio.create_task(self.bg_tasks._run_task(task_id))

        start_time = time.time()
        await self.bg_tasks.shutdown(timeout=5.0)
        end_time = time.time()

        # Should complete after task finishes but within reasonable time
        self.assertLess(end_time - start_time, 1)
        self.assertTrue(self.bg_tasks._is_server_shutting_down)
