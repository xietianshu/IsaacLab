.. _deployment-docker:


Docker Guide
============

.. caution::

    Due to the dependency on Isaac Sim docker image, by running this container you are implicitly
    agreeing to the `NVIDIA Omniverse EULA`_. If you do not agree to the EULA, do not run this container.

Setup Instructions
------------------

.. note::

    The following steps are taken from the NVIDIA Omniverse Isaac Sim documentation on `container installation`_.
    They have been added here for the sake of completeness.


Docker and Docker Compose
~~~~~~~~~~~~~~~~~~~~~~~~~

We have tested the container using Docker Engine version 26.0.0 and Docker Compose version 2.25.0
We recommend using these versions or newer.

* To install Docker, please follow the instructions for your operating system on the `Docker website`_.
* To install Docker Compose, please follow the instructions for your operating system on the `docker compose`_ page.
* Follow the post-installation steps for Docker on the `post-installation steps`_ page. These steps allow you to run
  Docker without using ``sudo``.
* To build and run GPU-accelerated containers, you also need install the `NVIDIA Container Toolkit`_.
  Please follow the instructions on the `Container Toolkit website`_ for installation steps.

.. note::

    Due to limitations with `snap <https://snapcraft.io/docs/home-outside-home>`_, please make sure
    the Isaac Lab directory is placed under the ``/home`` directory tree when using docker.


Obtaining the Isaac Sim Container
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* Get access to the `Isaac Sim container`_ by joining the NVIDIA Developer Program credentials.
* Generate your `NGC API key`_ to access locked container images from NVIDIA GPU Cloud (NGC).

  * This step requires you to create an NGC account if you do not already have one.
  * You would also need to install the NGC CLI to perform operations from the command line.
  * Once you have your generated API key and have installed the NGC CLI, you need to log in to NGC
    from the terminal.

    .. code:: bash

        ngc config set

* Use the command line to pull the Isaac Sim container image from NGC.

  .. code:: bash

      docker login nvcr.io

  * For the username, enter ``$oauthtoken`` exactly as shown. It is a special username that is used to
    authenticate with NGC.

    .. code:: text

        Username: $oauthtoken
        Password: <Your NGC API Key>


Directory Organization
----------------------

The root of the Isaac Lab repository contains the ``docker`` directory that has various files and scripts
needed to run Isaac Lab inside a Docker container. A subset of these are summarized below:

* ``Dockerfile``: Defines the isaac-lab images by overlaying Isaac Lab dependencies in various stages onto the Isaac Sim Docker image.
* ``cfgs/base.yaml``: Defines the compose project for the ``base`` stage in ``Dockerfile``. The ``ros2.yaml`` and ``custom.yaml`` files
  `extend`_ the ``isaac-lab`` service from ``base.yaml`` and do the same for their corresponding stages in the ``Dockerfile``.
* ``cfgs/isaacsim_volumes.yaml``: Defines several named volumes such as ``isaac-cache-kit`` to
  store frequently re-used resources compiled by Isaac Sim, such as shaders, and to retain logs, data, and documents.
<<<<<<< HEAD
* ``cfgs/isaaclab_volumes.yaml``: Defines bind-mounts to allow direct editing of Isaac Lab code from the host machine that runs
  the container, as well as a few volumes for storing logs and data. See ``container.py copy`` for more information on accessing
  this data on the host machine.
* ``.env``: Stores environment variables which are used directly in the defining the image, or else
  interpolated in the various ``cfg`` yaml files.
=======
* ``base.env``: Stores environment variables required for the ``base`` build process and the container itself. ``.env``
  files which end with something else (i.e. ``.env.ros2``) define these for `image_extension <#isaac-lab-image-extensions>`_.
>>>>>>> main
* ``container.py``: A script that interfaces with tools in ``utils`` to configure and build the image,
  and run and interact with the container.

Running the Container
---------------------

.. note::

    The docker container copies all the files from the repository into the container at the
    location ``/workspace/isaaclab`` at build time. This means that any changes made to the files in the container would not
    normally be reflected in the repository after the image has been built, i.e. after ``python container.py start`` is run.

    For a faster development cycle, we mount the following directories in the Isaac Lab repository into the container
    so that you can edit their files from the host machine:

    * ``source``: This is the directory that contains the Isaac Lab source code.
    * ``docs``: This is the directory that contains the source code for Isaac Lab documentation. This is overlaid except
      for the ``_build`` subdirectory where build artifacts are stored.


The script ``container.py`` parallels three basic ``docker compose`` commands. Each can accept an `image_extension argument <#isaac-lab-image-extensions>`_,
or else they will default to image_extension ``base``:

1. ``start``: This builds the image and brings up the container in detached mode (i.e. in the background).
<<<<<<< HEAD
2. ``build``: This builds the image but does not bring up the container.
3. ``config``: This outputs the compose.yaml which would be result from the inputs given to ``python container.py start``. This command is useful
   for debugging a compose configuration.
4. ``copy``: This copies the ``logs``, ``data_storage`` and ``docs/_build`` artifacts, from the ``isaac-lab-logs``, ``isaac-lab-data`` and ``isaac-lab-docs``
   volumes respectively, to the ``docker/artifacts`` directory. These artifacts persist between docker container instances and are shared between image extensions.
5. ``enter``: This begins a new bash process in an existing isaaclab container, and which can be exited
   without bringing down the container.
6. ``stop``: This brings down the container and removes it.
=======
2. ``enter``: This begins a new bash process in an existing isaaclab container, and which can be exited
   without bringing down the container.
3. ``config``: This outputs the compose.yaml which would be result from the inputs given to ``container.py start``. This command is useful
   for debugging a compose configuration.
4. ``copy``: This copies the ``logs``, ``data_storage`` and ``docs/_build`` artifacts, from the ``isaac-lab-logs``, ``isaac-lab-data`` and ``isaac-lab-docs``
   volumes respectively, to the ``docker/artifacts`` directory. These artifacts persist between docker container instances and are shared between image extensions.
5. ``stop``: This brings down the container and removes it.
>>>>>>> main

The following shows how to launch the container in a detached state and enter it:

.. code:: bash

    # Launch the container in detached mode
    # We don't pass an image extension arg, so it defaults to 'base'
    python docker/container.py start

    # If we want to add .env or .yaml files to customize our compose config,
    # we can simply specify them in the same manner as the compose cli
    # python docker/container.py start --file my-compose.yaml --env-file .env.my-vars

    # Enter the container
    # We pass 'base' explicitly, but if we hadn't it would default to 'base'
    python docker/container.py enter base

To copy files from the base container to the host machine, you can use the following command:

.. code:: bash

    # Copy the file /workspace/isaaclab/logs to the current directory
    docker cp isaac-lab-base:/workspace/isaaclab/logs .

The script ``container.py`` provides a wrapper around this command to copy the ``logs`` , ``data_storage`` and ``docs/_build``
directories to the ``docker/artifacts`` directory. This is useful for copying the logs, data and documentation:

.. code:: bash

    # stop the container
    python docker/container.py stop


X11 forwarding
~~~~~~~~~~~~~~

The container supports X11 forwarding, which allows the user to run GUI applications from the container and display them
on the host machine.

The first time a container is started with ``python docker/container.py start``, the script prompts
the user whether to activate X11 forwarding. This will create a file ``docker/.container.cfg`` to store the user's choice.
Subsequently, X11 forwarding can be toggled by changing ``__ISAACLAB_X11_FORWARDING_ENABLED`` to 0 or 1 in ``docker/.container.cfg``.


Python Interpreter
~~~~~~~~~~~~~~~~~~

The container uses the Python interpreter provided by Isaac Sim. This interpreter is located at
``/isaac-sim/python.sh``. We set aliases inside the container to make it easier to run the Python
interpreter. You can use the following commands to run the Python interpreter:

.. code:: bash

    # Run the Python interpreter -> points to /isaac-sim/python.sh
    python


Understanding the mounted volumes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``IsaacLabContainerInterface`` creates several named volumes that are mounted to the container by default.
These are summarized below:

isaacsim_volumes.yaml
~~~~~~~~~~~~~~~~~~~~~

* ``isaac-cache-kit``: This volume is used to store cached Kit resources (``/isaac-sim/kit/cache`` in container)
* ``isaac-cache-ov``: This volume is used to store cached OV resources (``/root/.cache/ov`` in container)
* ``isaac-cache-pip``: This volume is used to store cached pip resources (``/root/.cache/pip`` in container)
* ``isaac-cache-gl``: This volume is used to store cached GLCache resources (``/root/.cache/nvidia/GLCache`` in container)
* ``isaac-cache-compute``: This volume is used to store cached compute resources (``/root/.nv/ComputeCache`` in container)
* ``isaac-logs``: This volume is used to store logs generated by Omniverse. (``/root/.nvidia-omniverse/logs`` in container)
* ``isaac-carb-logs``: This volume is used to store logs generated by carb. (``/isaac-sim/kit/logs/Kit/Isaac-Sim`` in container)
* ``isaac-data``: This volume is used to store data generated by Omniverse. (``/root/.local/share/ov/data`` in container)
* ``isaac-docs``: This volume is used to store documents generated by Omniverse. (``/root/Documents`` in container)

isaaclab_volumes.yaml
~~~~~~~~~~~~~~~~~~~~~

* ``isaac-lab-docs``: This volume is used to store documentation of Isaac Lab when built inside the container. (``/workspace/isaaclab/docs/_build`` in container)
* ``isaac-lab-logs``: This volume is used to store logs generated by Isaac Lab workflows when run inside the container. (``/workspace/isaaclab/logs`` in container)
* ``isaac-lab-data``: This volume is used to store whatever data users may want to preserve between container runs. (``/workspace/isaaclab/data_storage`` in container)

To view the contents of these volumes, you can use the following command:

.. code:: bash

    # list all volumes
    docker volume ls
    # inspect a specific volume, e.g. isaac-cache-kit
    docker volume inspect isaac-cache-kit



Isaac Lab Target Stages
-----------------------

The produced image depends upon the arguments passed to ``container.py start`` and ``container.py stop``. These
<<<<<<< HEAD
commands accept a ``target`` as an additional argument, which reflect the `stages`_ within the Dockerfile. If no argument is passed, then these
commands default to ``base``. Currently, the only valid ``target`` arguments are (``base``, ``ros2``, ``custom``). ``cfgs/custom.yaml`` and
the ``custom`` Dockerfile stage are intended  to act as a template to demonstrate how one could add their own Dockerfile stage and use it
with the ``IsaacLabContainerInterface``. Only one ``target`` can be passed at a time, and the produced container will be named ``isaac-lab-${target}``.
=======
commands accept an ``image_extension`` as an additional argument. If no argument is passed, then these
commands default to ``base``. Currently, the only valid ``image_extension`` arguments are (``base``, ``ros2``).
Only one ``image_extension`` can be passed at a time, and the produced container will be named ``isaac-lab-${profile}``.
>>>>>>> main

.. code:: bash

    # start base by default
    python docker/container.py start
    # stop base explicitly
    python docker/container.py stop base
    # start ros2 container
    python docker/container.py start ros2
    # stop ros2 container
    python docker/container.py stop ros2

The passed ``target`` argument will build the image defined in ``Dockerfile`` up the stage ``target``,
with the corresponding ``.yaml`` in the ``docker/cfgs`` directory, down the chain of `extensions`_.

ROS2 Image Stage
~~~~~~~~~~~~~~~~

In ``Dockerfile`` stage ``ros2``, the image installs ROS2 Humble via an `apt package`_, and it is sourced in the ``.bashrc``.
The exact version is specified by the variable ``ROS_APT_PACKAGE`` in the ``cfgs/ros2.yaml`` file,
defaulting to ``ros-base``. Other relevant ROS2 variables are also specified in the ``cfgs/ros2.yaml`` file,
including variables defining the `various middleware`_ options. The container defaults to ``FastRTPS``, but ``CylconeDDS``
is also supported. Each of these middlewares can be `tuned`_ using their corresponding ``.xml`` files under ``docker/.ros``.


Known Issues
------------

Invalid mount config for type "bind"
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you see the following error when building the container:

.. code:: text

    ⠋ Container isaaclab  Creating                                                                                                                                                                         0.0s
    Error response from daemon: invalid mount config for type "bind": bind source path does not exist: ${HOME}/.Xauthority

This means that the ``.Xauthority`` file is not present in the home directory of the host machine.
This shouldn't happen as we construct and mount a valid ``.xauth`` file under the ``__ISAACLAB_TMP_DIR``, defined in
``cfgs/x11.yaml``. If this occurs, try deleting the ``.container.cfg`` file and restarting the container.

.. code:: text

    ⠋ Container isaaclab  Creating                                                                                                                                                                         0.0s
    Error response from daemon: invalid mount config for type "bind": bind source path does not exist: /tmp/.X11-unix

This means that the folder/files are either not present or not accessible on the host machine.
This usually happens when you have multiple docker versions installed on your machine. To fix
this, you can try the following:

* Remove all docker versions from your machine.

  .. code:: bash

      sudo apt remove docker*
      sudo apt remove docker docker-engine docker.io containerd runc docker-desktop docker-compose-plugin
      sudo snap remove docker
      sudo apt clean autoclean && sudo apt autoremove --yes

* Install the latest version of docker based on the instructions in the setup section.

WebRTC Streaming
~~~~~~~~~~~~~~~~

When streaming the GUI from Isaac Sim, there are `several streaming clients`_ available. There is a `known issue`_ when
attempting to use WebRTC streaming client on Google Chrome and Safari while running Isaac Sim inside a container.
To avoid this problem, we suggest using the Native Streaming Client or using the
Mozilla Firefox browser on which WebRTC works.

Streaming is the only supported method for visualizing the Isaac GUI from within the container. The Omniverse Streaming Client
is freely available from the Omniverse app, and is easy to use. The other streaming methods similarly require only a web browser.
If users want to use X11 forwarding in order to have the apps behave as local GUI windows, they can enable it at runtime
or in the ``.container.cfg``.


.. _`NVIDIA Omniverse EULA`: https://docs.omniverse.nvidia.com/platform/latest/common/NVIDIA_Omniverse_License_Agreement.html
.. _`container installation`: https://docs.omniverse.nvidia.com/isaacsim/latest/installation/install_container.html
.. _`Docker website`: https://docs.docker.com/desktop/install/linux-install/
.. _`docker compose`: https://docs.docker.com/compose/install/linux/#install-using-the-repository
.. _`NVIDIA Container Toolkit`: https://github.com/NVIDIA/nvidia-container-toolkit
.. _`Container Toolkit website`: https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html
.. _`post-installation steps`: https://docs.docker.com/engine/install/linux-postinstall/
.. _`Isaac Sim container`: https://catalog.ngc.nvidia.com/orgs/nvidia/containers/isaac-sim
.. _`NGC API key`: https://docs.nvidia.com/ngc/gpu-cloud/ngc-user-guide/index.html#generating-api-key
.. _`extend`: https://docs.docker.com/compose/multiple-compose-files/extends/
.. _`extensions`: https://docs.docker.com/compose/multiple-compose-files/extends/
.. _`several streaming clients`: https://docs.omniverse.nvidia.com/isaacsim/latest/installation/manual_livestream_clients.html
.. _`known issue`: https://forums.developer.nvidia.com/t/unable-to-use-webrtc-when-i-run-runheadless-webrtc-sh-in-remote-headless-container/222916
.. _`stages`: https://docs.docker.com/build/building/multi-stage/
.. _`profile`: https://docs.docker.com/compose/compose-file/15-profiles/
.. _`apt package`: https://docs.ros.org/en/humble/Installation/Ubuntu-Install-Debians.html#install-ros-2-packages
.. _`various middleware`: https://docs.ros.org/en/humble/How-To-Guides/Working-with-multiple-RMW-implementations.html
.. _`tuned`: https://docs.ros.org/en/foxy/How-To-Guides/DDS-tuning.html
