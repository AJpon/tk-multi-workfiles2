# Copyright (c) 2026 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

"""
Unit tests for FileFormBase._build_entity_models.
"""

from types import SimpleNamespace
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import patch

from tank_test.tank_test_base import setUpModule  # noqa
from workfiles2_test_base import Workfiles2TestBase
from workfiles2_test_base import tearDownModule  # noqa

ASSET_TASKS_UNDER_SHOTS = {
    "caption": "Shots",
    "entity_type": "Shot",
    "hierarchy": ["code"],
    "step_filter_on": "Asset",
    "sub_hierarchy": {
        "entity_type": "Task",
        "link_field": "entity.Asset.shots",
        "hierarchy": ["step"],
    },
}


class TestBuildEntityModels(Workfiles2TestBase):
    """
    Test how the "entities" setting is turned into models and step filters.
    """

    def setUp(self) -> None:
        """
        Set up the test fixtures.
        """
        super().setUp()

        from sgtk.platform.qt import QtCore

        self._models = []

        # FileFormBase._build_entity_models only needs the background task
        # manager from its instance, so a bare QObject is enough.
        self._form_stub = QtCore.QObject()
        self._form_stub._bg_task_manager = self.bg_task_manager

    def tearDown(self) -> None:
        """
        Destroy the models before the engine and the task manager go away.
        """
        for model in self._models:
            model.destroy()
        self._models = []
        super().tearDown()
        self._form_stub = None

    def _build(
        self, entities: List[Dict[str, Any]]
    ) -> List[Tuple[str, Optional[str], Any]]:
        """
        Build the entity models for the given "entities" setting.

        :param entities: The value of the "entities" setting.
        :returns: A list of (caption, step_filter_on, model) tuples.
        """
        file_form_base = self.tk_multi_workfiles.file_form_base

        def get_setting(key: str, default: Any = None) -> Any:
            return entities if key == "entities" else default

        # Only the module under test sees the patched current_bundle. Patching
        # it on sgtk.platform would also affect the frameworks, which rely on
        # it to find themselves.
        fake_sgtk = SimpleNamespace(
            platform=SimpleNamespace(current_bundle=lambda: self.app)
        )

        with patch.object(file_form_base, "sgtk", fake_sgtk), patch.object(
            self.app, "get_setting", side_effect=get_setting
        ), patch.object(file_form_base, "get_saved_step_filter", return_value=None):
            result = file_form_base.FileFormBase._build_entity_models(self._form_stub)
        self._models.extend(model for _, _, model in result)
        return result

    def _with_opt_in(
        self, value: Any, entity: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Return a copy of a tab with use_step_filter_on set in its sub_hierarchy.

        :param value: The value of use_step_filter_on.
        :param entity: The tab to copy, ASSET_TASKS_UNDER_SHOTS by default.
        :returns: The new tab.
        """
        entity = dict(entity or ASSET_TASKS_UNDER_SHOTS)
        entity["sub_hierarchy"] = dict(
            entity["sub_hierarchy"], use_step_filter_on=value
        )
        return entity

    def test_step_filter_on_is_overwritten_without_opt_in(self) -> None:
        """
        Without use_step_filter_on, step_filter_on is overwritten with the
        entity type of the tab, as before.
        """
        ((_, step_filter_on, _),) = self._build([ASSET_TASKS_UNDER_SHOTS])
        self.assertEqual(step_filter_on, "Shot")

    def test_step_filter_on_is_overwritten_when_opt_in_is_false(self) -> None:
        """
        With use_step_filter_on set to false, step_filter_on is overwritten
        with the entity type of the tab, as before.
        """
        ((_, step_filter_on, _),) = self._build([self._with_opt_in(False)])
        self.assertEqual(step_filter_on, "Shot")

    def test_step_filter_on_is_kept_when_opt_in_is_true(self) -> None:
        """
        With use_step_filter_on set to true, step_filter_on is kept.
        """
        ((_, step_filter_on, _),) = self._build([self._with_opt_in(True)])
        self.assertEqual(step_filter_on, "Asset")

    def test_main_entity_type_is_used_when_opt_in_without_step_filter_on(
        self,
    ) -> None:
        """
        With use_step_filter_on set to true but no step_filter_on, the browser
        form falls back to the entity type of the model.
        """
        entity = self._with_opt_in(True)
        del entity["step_filter_on"]
        ((_, step_filter_on, model),) = self._build([entity])
        self.assertIsNone(step_filter_on)
        self.assertEqual(step_filter_on or model.get_entity_type(), "Shot")

    def test_opt_in_applies_per_tab(self) -> None:
        """
        use_step_filter_on only applies to the tab that sets it.
        """
        result = self._build([self._with_opt_in(True), ASSET_TASKS_UNDER_SHOTS])
        self.assertEqual(
            [step_filter_on for _, step_filter_on, _ in result], ["Asset", "Shot"]
        )
