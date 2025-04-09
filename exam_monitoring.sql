-- phpMyAdmin SQL Dump
-- version 4.1.12
-- http://www.phpmyadmin.net
--
-- Host: 127.0.0.1
-- Generation Time: Apr 09, 2025 at 12:51 PM
-- Server version: 5.6.16
-- PHP Version: 5.5.11
SET FOREIGN_KEY_CHECKS = 0;
SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8 */;

--
-- Database: `exam_monitoring`
--

-- --------------------------------------------------------

--
-- Table structure for table `app_lecturehall`
--

CREATE TABLE IF NOT EXISTS `app_lecturehall` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `building` varchar(50) NOT NULL,
  `hall_name` varchar(50) NOT NULL,
  `assigned_teacher_id` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `assigned_teacher_id` (`assigned_teacher_id`)
) ENGINE=InnoDB  DEFAULT CHARSET=latin1 AUTO_INCREMENT=10 ;

--
-- Dumping data for table `app_lecturehall`
--

INSERT INTO `app_lecturehall` (`id`, `building`, `hall_name`, `assigned_teacher_id`) VALUES
(1, 'Main Building', 'LH1', 4),
(2, 'KE Block', 'LH2', 7),
(3, 'Main Building', 'LH2', NULL),
(4, 'KE Block', 'LH1', 6),
(5, 'Main Building', 'LH3', NULL),
(6, 'KE Block', 'LH4', NULL),
(7, 'KE Block', 'LH15', NULL),
(8, 'PG Block', 'Hall-1, Block A', 5),
(9, 'PG Block', 'Hall-1, Block B', NULL);

-- --------------------------------------------------------

--
-- Table structure for table `app_malpraticedetection`
--

CREATE TABLE IF NOT EXISTS `app_malpraticedetection` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `date` date DEFAULT NULL,
  `time` time(6) DEFAULT NULL,
  `malpractice` varchar(150) NOT NULL,
  `proof` varchar(150) NOT NULL,
  `verified` tinyint(1) NOT NULL,
  `is_malpractice` tinyint(1) DEFAULT NULL,
  `lecture_hall_id` bigint(20) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `app_malpraticedetection_lecture_hall_id_09c5c08d` (`lecture_hall_id`)
) ENGINE=InnoDB  DEFAULT CHARSET=latin1 AUTO_INCREMENT=2517 ;

-- --------------------------------------------------------

--
-- Table structure for table `app_teacherprofile`
--

CREATE TABLE IF NOT EXISTS `app_teacherprofile` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `phone` varchar(20) NOT NULL,
  `profile_picture` varchar(100) NOT NULL,
  `user_id` int(11) NOT NULL,
  `lecture_hall_id` bigint(20) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `user_id` (`user_id`),
  UNIQUE KEY `lecture_hall_id` (`lecture_hall_id`)
) ENGINE=InnoDB  DEFAULT CHARSET=latin1 AUTO_INCREMENT=8 ;

--
-- Dumping data for table `app_teacherprofile`
--

INSERT INTO `app_teacherprofile` (`id`, `phone`, `profile_picture`, `user_id`, `lecture_hall_id`) VALUES
(1, '9188022697', 'profile_pics/WIN_20250223_20_13_37_Pro_k5Fb3ah.jpg', 4, 2),
(2, '7042027369', 'profile_pics/WIN_20250223_20_13_38_Pro.jpg', 5, NULL),
(5, '', '', 1, NULL),
(6, '6238817929', 'profile_pics/WIN_20250223_20_13_37_Pro_luOswoN.jpg', 6, NULL),
(7, '9778440435', 'profile_pics/WIN_20250223_20_13_32_Pro_2.jpg', 7, NULL);

-- --------------------------------------------------------

--
-- Table structure for table `auth_group`
--

CREATE TABLE IF NOT EXISTS `auth_group` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(150) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 AUTO_INCREMENT=1 ;

-- --------------------------------------------------------

--
-- Table structure for table `auth_group_permissions`
--

CREATE TABLE IF NOT EXISTS `auth_group_permissions` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `group_id` int(11) NOT NULL,
  `permission_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_group_permissions_group_id_permission_id_0cd325b0_uniq` (`group_id`,`permission_id`),
  KEY `auth_group_permissio_permission_id_84c5c92e_fk_auth_perm` (`permission_id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 AUTO_INCREMENT=1 ;

-- --------------------------------------------------------

--
-- Table structure for table `auth_permission`
--

CREATE TABLE IF NOT EXISTS `auth_permission` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `content_type_id` int(11) NOT NULL,
  `codename` varchar(100) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_permission_content_type_id_codename_01ab375a_uniq` (`content_type_id`,`codename`)
) ENGINE=InnoDB  DEFAULT CHARSET=latin1 AUTO_INCREMENT=45 ;

--
-- Dumping data for table `auth_permission`
--

INSERT INTO `auth_permission` (`id`, `name`, `content_type_id`, `codename`) VALUES
(1, 'Can add log entry', 1, 'add_logentry'),
(2, 'Can change log entry', 1, 'change_logentry'),
(3, 'Can delete log entry', 1, 'delete_logentry'),
(4, 'Can view log entry', 1, 'view_logentry'),
(5, 'Can add permission', 2, 'add_permission'),
(6, 'Can change permission', 2, 'change_permission'),
(7, 'Can delete permission', 2, 'delete_permission'),
(8, 'Can view permission', 2, 'view_permission'),
(9, 'Can add group', 3, 'add_group'),
(10, 'Can change group', 3, 'change_group'),
(11, 'Can delete group', 3, 'delete_group'),
(12, 'Can view group', 3, 'view_group'),
(13, 'Can add user', 4, 'add_user'),
(14, 'Can change user', 4, 'change_user'),
(15, 'Can delete user', 4, 'delete_user'),
(16, 'Can view user', 4, 'view_user'),
(17, 'Can add content type', 5, 'add_contenttype'),
(18, 'Can change content type', 5, 'change_contenttype'),
(19, 'Can delete content type', 5, 'delete_contenttype'),
(20, 'Can view content type', 5, 'view_contenttype'),
(21, 'Can add session', 6, 'add_session'),
(22, 'Can change session', 6, 'change_session'),
(23, 'Can delete session', 6, 'delete_session'),
(24, 'Can view session', 6, 'view_session'),
(25, 'Can add regtable', 7, 'add_regtable'),
(26, 'Can change regtable', 7, 'change_regtable'),
(27, 'Can delete regtable', 7, 'delete_regtable'),
(28, 'Can view regtable', 7, 'view_regtable'),
(29, 'Can add malpratice_detection', 8, 'add_malpratice_detection'),
(30, 'Can change malpratice_detection', 8, 'change_malpratice_detection'),
(31, 'Can delete malpratice_detection', 8, 'delete_malpratice_detection'),
(32, 'Can view malpratice_detection', 8, 'view_malpratice_detection'),
(33, 'Can add teacher profile', 9, 'add_teacherprofile'),
(34, 'Can change teacher profile', 9, 'change_teacherprofile'),
(35, 'Can delete teacher profile', 9, 'delete_teacherprofile'),
(36, 'Can view teacher profile', 9, 'view_teacherprofile'),
(37, 'Can add malpratice detection', 10, 'add_malpraticedetection'),
(38, 'Can change malpratice detection', 10, 'change_malpraticedetection'),
(39, 'Can delete malpratice detection', 10, 'delete_malpraticedetection'),
(40, 'Can view malpratice detection', 10, 'view_malpraticedetection'),
(41, 'Can add lecture hall', 11, 'add_lecturehall'),
(42, 'Can change lecture hall', 11, 'change_lecturehall'),
(43, 'Can delete lecture hall', 11, 'delete_lecturehall'),
(44, 'Can view lecture hall', 11, 'view_lecturehall');

-- --------------------------------------------------------

--
-- Table structure for table `auth_user`
--

CREATE TABLE IF NOT EXISTS `auth_user` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `password` varchar(128) NOT NULL,
  `last_login` datetime(6) DEFAULT NULL,
  `is_superuser` tinyint(1) NOT NULL,
  `username` varchar(150) NOT NULL,
  `first_name` varchar(150) NOT NULL,
  `last_name` varchar(150) NOT NULL,
  `email` varchar(254) NOT NULL,
  `is_staff` tinyint(1) NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `date_joined` datetime(6) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`)
) ENGINE=InnoDB  DEFAULT CHARSET=latin1 AUTO_INCREMENT=8 ;

--
-- Dumping data for table `auth_user`
--

INSERT INTO `auth_user` (`id`, `password`, `last_login`, `is_superuser`, `username`, `first_name`, `last_name`, `email`, `is_staff`, `is_active`, `date_joined`) VALUES
(1, 'pbkdf2_sha256$260000$eqelb4KFYZ4otZOcPocddV$BzkDhHOridis9Vz/7lTDtUJTG8S1TSlIVnRLlber7PY=', '2025-04-08 16:39:26.127950', 1, 'detectsus', 'Admin', '', 'detectsus@gmail.com', 1, 1, '2025-03-25 07:46:54.000000'),
(4, 'pbkdf2_sha256$260000$6CAfF6YfrLBNKTu6cLBHpL$CgPAsUCluyM7XXjP69Vub06lgRYeagjQuGhw6ToDEqg=', '2025-04-03 07:58:17.530307', 0, 'noelmathen', 'Noel', 'Mathen', 'noelmathen03@gmail.com', 0, 1, '2025-03-25 10:18:35.969189'),
(5, 'pbkdf2_sha256$260000$OerZgZjroimtn3wdbWsEnV$ZfhMcGhb54GyD9Cbh/nlahzte2jLEjw3BgmhszFygOE=', '2025-04-08 16:44:23.507390', 0, 'shrutishibu', 'Shruti', 'Shibu', 'sshrutishibu@gmail.com', 0, 1, '2025-03-27 12:14:26.482698'),
(6, 'pbkdf2_sha256$260000$VdVpCLQQduIlKlE5Mdy0RU$i26YWKEn+vvmQcbgFmH+tOqLG/jkucpyAqrJXKB/JTA=', '2025-04-01 18:34:09.814838', 0, 'allenprince', 'Allen', 'Prince', 'prince.allen1820@gmail.com', 0, 1, '2025-04-01 18:30:46.683576'),
(7, 'pbkdf2_sha256$260000$kbBlOBAUFPuIYagXYN1Prg$cU0Lfr0ISdYaMwqJG/X8Ur3jh+RTQ7IyzbGCjagFI8M=', '2025-04-01 18:34:44.330588', 0, 'deaeliz', 'Dea', 'Elizabeth Varghese', 'deaeliz49@gmail.com', 0, 1, '2025-04-01 18:32:39.314193');

-- --------------------------------------------------------

--
-- Table structure for table `auth_user_groups`
--

CREATE TABLE IF NOT EXISTS `auth_user_groups` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `group_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_user_groups_user_id_group_id_94350c0c_uniq` (`user_id`,`group_id`),
  KEY `auth_user_groups_group_id_97559544_fk_auth_group_id` (`group_id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 AUTO_INCREMENT=1 ;

-- --------------------------------------------------------

--
-- Table structure for table `auth_user_user_permissions`
--

CREATE TABLE IF NOT EXISTS `auth_user_user_permissions` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `permission_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_user_user_permissions_user_id_permission_id_14a6b632_uniq` (`user_id`,`permission_id`),
  KEY `auth_user_user_permi_permission_id_1fbb5f2c_fk_auth_perm` (`permission_id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 AUTO_INCREMENT=1 ;

-- --------------------------------------------------------

--
-- Table structure for table `django_admin_log`
--

CREATE TABLE IF NOT EXISTS `django_admin_log` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `action_time` datetime(6) NOT NULL,
  `object_id` longtext,
  `object_repr` varchar(200) NOT NULL,
  `action_flag` smallint(5) unsigned NOT NULL,
  `change_message` longtext NOT NULL,
  `content_type_id` int(11) DEFAULT NULL,
  `user_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `django_admin_log_content_type_id_c4bce8eb_fk_django_co` (`content_type_id`),
  KEY `django_admin_log_user_id_c564eba6_fk_auth_user_id` (`user_id`)
) ENGINE=InnoDB  DEFAULT CHARSET=latin1 AUTO_INCREMENT=5 ;

--
-- Dumping data for table `django_admin_log`
--

INSERT INTO `django_admin_log` (`id`, `action_time`, `object_id`, `object_repr`, `action_flag`, `change_message`, `content_type_id`, `user_id`) VALUES
(1, '2025-03-25 10:18:24.020268', '2', 'noelmathen', 3, '', 4, 1),
(2, '2025-03-25 10:34:13.920329', '1', 'detectsus', 2, '[]', 4, 1),
(3, '2025-03-27 12:26:45.746484', '6', 'shrutishibuu', 3, '', 4, 1),
(4, '2025-03-27 12:26:45.747484', '7', 'shrutishibuuu', 3, '', 4, 1);

-- --------------------------------------------------------

--
-- Table structure for table `django_content_type`
--

CREATE TABLE IF NOT EXISTS `django_content_type` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `app_label` varchar(100) NOT NULL,
  `model` varchar(100) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `django_content_type_app_label_model_76bd3d3b_uniq` (`app_label`,`model`)
) ENGINE=InnoDB  DEFAULT CHARSET=latin1 AUTO_INCREMENT=12 ;

--
-- Dumping data for table `django_content_type`
--

INSERT INTO `django_content_type` (`id`, `app_label`, `model`) VALUES
(1, 'admin', 'logentry'),
(11, 'app', 'lecturehall'),
(10, 'app', 'malpraticedetection'),
(8, 'app', 'malpratice_detection'),
(7, 'app', 'regtable'),
(9, 'app', 'teacherprofile'),
(3, 'auth', 'group'),
(2, 'auth', 'permission'),
(4, 'auth', 'user'),
(5, 'contenttypes', 'contenttype'),
(6, 'sessions', 'session');

-- --------------------------------------------------------

--
-- Table structure for table `django_migrations`
--

CREATE TABLE IF NOT EXISTS `django_migrations` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `app` varchar(255) NOT NULL,
  `name` varchar(255) NOT NULL,
  `applied` datetime(6) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB  DEFAULT CHARSET=latin1 AUTO_INCREMENT=33 ;

--
-- Dumping data for table `django_migrations`
--

INSERT INTO `django_migrations` (`id`, `app`, `name`, `applied`) VALUES
(1, 'contenttypes', '0001_initial', '2025-03-11 16:54:48.615159'),
(2, 'auth', '0001_initial', '2025-03-11 16:54:49.185329'),
(3, 'admin', '0001_initial', '2025-03-11 16:54:49.283243'),
(4, 'admin', '0002_logentry_remove_auto_add', '2025-03-11 16:54:49.290259'),
(5, 'admin', '0003_logentry_add_action_flag_choices', '2025-03-11 16:54:49.297924'),
(6, 'app', '0001_initial', '2025-03-11 16:54:49.353542'),
(7, 'app', '0002_interviewanalysis_resume_analysis', '2025-03-11 16:54:49.395624'),
(8, 'app', '0003_auto_20250311_1410', '2025-03-11 16:54:49.428962'),
(9, 'contenttypes', '0002_remove_content_type_name', '2025-03-11 16:54:49.510286'),
(10, 'auth', '0002_alter_permission_name_max_length', '2025-03-11 16:54:49.552530'),
(11, 'auth', '0003_alter_user_email_max_length', '2025-03-11 16:54:49.593565'),
(12, 'auth', '0004_alter_user_username_opts', '2025-03-11 16:54:49.602218'),
(13, 'auth', '0005_alter_user_last_login_null', '2025-03-11 16:54:49.650174'),
(14, 'auth', '0006_require_contenttypes_0002', '2025-03-11 16:54:49.655203'),
(15, 'auth', '0007_alter_validators_add_error_messages', '2025-03-11 16:54:49.669374'),
(16, 'auth', '0008_alter_user_username_max_length', '2025-03-11 16:54:49.715583'),
(17, 'auth', '0009_alter_user_last_name_max_length', '2025-03-11 16:54:49.765131'),
(18, 'auth', '0010_alter_group_name_max_length', '2025-03-11 16:54:49.831397'),
(19, 'auth', '0011_update_proxy_permissions', '2025-03-11 16:54:49.849879'),
(20, 'auth', '0012_alter_user_first_name_max_length', '2025-03-11 16:54:49.902419'),
(21, 'sessions', '0001_initial', '2025-03-11 16:54:49.961365'),
(22, 'app', '0004_auto_20250324_1111', '2025-03-24 05:46:43.837458'),
(23, 'app', '0005_auto_20250325_1547', '2025-03-25 10:17:29.444413'),
(24, 'app', '0006_auto_20250325_1609', '2025-03-25 10:39:51.112795'),
(25, 'app', '0007_auto_20250325_1726', '2025-03-25 11:56:50.335428'),
(26, 'app', '0008_auto_20250327_1340', '2025-03-27 08:10:31.114939'),
(27, 'app', '0009_remove_teacherprofile_lecture_halls', '2025-03-27 08:14:42.482166'),
(28, 'app', '0010_teacherprofile_lecture_hall', '2025-03-27 10:10:35.352825'),
(29, 'app', '0011_rename_lecture_hall_teacherprofile_lecture_halls', '2025-03-27 10:10:35.397212'),
(30, 'app', '0012_rename_lecture_halls_teacherprofile_lecture_hall', '2025-03-27 10:10:35.449858'),
(31, 'app', '0013_alter_malpraticedetection_lecture_hall', '2025-03-27 11:57:38.097468'),
(32, 'app', '0014_alter_lecturehall_building', '2025-04-09 08:27:30.512668');

-- --------------------------------------------------------

--
-- Table structure for table `django_session`
--

CREATE TABLE IF NOT EXISTS `django_session` (
  `session_key` varchar(40) NOT NULL,
  `session_data` longtext NOT NULL,
  `expire_date` datetime(6) NOT NULL,
  PRIMARY KEY (`session_key`),
  KEY `django_session_expire_date_a5c62663` (`expire_date`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

--
-- Dumping data for table `django_session`
--

INSERT INTO `django_session` (`session_key`, `session_data`, `expire_date`) VALUES
('1761h7zshpdrqgn92ens677mk14qe2vz', 'e30:1tsF1P:rDCQfCxspEQzevm7faFnHSUhpAc430qgFjdFI2-jAGk', '2025-03-26 05:52:51.173152'),
('1lw92qofg2bnubhdpbzfp65o2mxuaemp', 'e30:1tx0Hy:2aLlCePZKTOFs7-ckN8oP8xUoe_47-RFiNapfJGdL4c', '2025-04-08 09:09:38.036264'),
('5pznjlm67g80lgck1bk4c1t0o8aq1gyl', '.eJyrVkpMyc3Mc0jPTczM0UvOz1WywhDRgYjAZJRqAfXkEjs:1tsF4X:hIj0SEqOhSOrUD42YaDt8_P7OW-iLk9nKL_6fyzSW7I', '2025-03-26 05:56:05.998932'),
('6tncfh4mtsm4nunror27us5fusd48s1j', '.eJxVjMEOgjAQRP-lZ9O0QNmWo3e_oVl2t4KaNilwMv67kHDQ22TmzXuriNs6xW2RGmdWg3Lq8tuNSE_Jx8APzPeiqeS1zqM-EH2ui74Vltf1ZP8EEy7T_u5DJz2jMcTi2943iTzY0FiC5MdOxGJy4AADNxg8pJYMgBgPvGdnd2kVKpUjlS2varDm8wUNtz3b:1u2C7B:w66C_plXCZIw6BIvnqK_dwmffFGxcsA3HYfQ7lod78E', '2025-04-22 16:47:57.279604'),
('az3dhlks8rksy28om5eqten7uyu7odqr', '.eJxVjEEOwiAQRe_C2pBBhhZcuvcMZIahUjU0Ke3KeHfbpAvd_vfef6tI61Li2vIcR1EXher0uzGlZ647kAfV-6TTVJd5ZL0r-qBN3ybJr-vh_h0UamWrOzKE1iCx8X1AA8Hy4M7WuYGFIFFKZHsMlgCYEQSsBA85-y3sglGfL9XgN6o:1tx2Rp:QFeCwHphdjf9CFizO7GqIj16mCHWJiQARwjWnQT8yB0', '2025-04-08 11:27:57.121459'),
('jqgk8f7cbw1ggptsfmirnr6rkj0clxfp', '.eJxVjEEOwiAQRe_C2hBgRMCl-56BTIdBqgaS0q6Md7dNutDtf-_9t4i4LiWunec4JXEVWpx-txHpyXUH6YH13iS1uszTKHdFHrTLoSV-3Q7376BgL1udCcF4y_qMNrO_uGAwKQ2AwRjwnFGRsoQqGOWzBbdpiRwhBwej1eLzBeSpN_c:1txmJV:mRLueXUKFHLDgIeCzUyhQT1RXuFBSB_pSOTPQRPV9_g', '2025-04-10 12:26:25.255043'),
('k17fit3bco0k2kt8ff5th5c029zbbim7', '.eJxVjkEOwiAURO_C2hAKpUCX7j0D-Xw-tmoggXZlvLsl6UK3895M5s087Nvi90bVr5HNbGCX3ywAPil3EB-Q74VjyVtdA-8KP2njtxLpdT3dv4EF2nK0E4KSVtMwgk5kJ-MkRDEoBU5KZSmBQKERhJPCJq3MoUU0COSMCrq_qoSlRo9lzxub5TiJzxeJWz50:1u2Qd4:slSrrnXCsVli-Pew2_NQw0-VLb57Rm-HhdNZlHBAAU0', '2025-04-23 08:17:50.549133'),
('oybciw9jp96gvi22xei6qkbju45kzyjx', '.eJxVjMEOgjAQRP-lZ9O0QNmWo3e_oVl2t4KaNilwMv67kHDQ22TmzXuriNs6xW2RGmdWg3Lq8tuNSE_Jx8APzPeiqeS1zqM-EH2ui74Vltf1ZP8EEy7T_u5DJz2jMcTi2943iTzY0FiC5MdOxGJy4AADNxg8pJYMgBgPvGdnd2kVKpUjlS2vavCfL9AoPbI:1u0GEK:fraE-QgJeGZKer6NRZnMhw123DX69qYS7IFFLA6adgU', '2025-04-17 08:47:20.560945'),
('twfdocd1084roqjkrfv28oncliv40bny', '.eJxVjsEOwiAQRP-FsyGUlQI9eu83kO2y2KqBBNqT8d9tkx70Ou_NZN4i4LbOYWtcwxLFIDpx-c0mpCfnA8QH5nuRVPJal0keijxpk2OJ_Lqd7t_AjG3e24kQtDPcXdEkdr31GqPqANBrDY4TKlKGUHmtXDJgdy2SJWRvYTLHq8pUagxUtryKQYPtP1-JZj56:1u2C5q:bFx6g4uh81UhSdPpeK7BHNJ8dr3FRh6jcAI1gUF9Ap0', '2025-04-22 16:46:34.581128');

--
-- Constraints for dumped tables
--

--
-- Constraints for table `app_lecturehall`
--
ALTER TABLE `app_lecturehall`
  ADD CONSTRAINT `app_lecturehall_assigned_teacher_id_4268141c_fk_auth_user_id` FOREIGN KEY (`assigned_teacher_id`) REFERENCES `auth_user` (`id`);

--
-- Constraints for table `app_malpraticedetection`
--
ALTER TABLE `app_malpraticedetection`
  ADD CONSTRAINT `app_malpraticedetect_lecture_hall_id_09c5c08d_fk_app_lectu` FOREIGN KEY (`lecture_hall_id`) REFERENCES `app_lecturehall` (`id`);

--
-- Constraints for table `app_teacherprofile`
--
ALTER TABLE `app_teacherprofile`
  ADD CONSTRAINT `app_teacherprofile_lecture_hall_id_608352da_fk_app_lectu` FOREIGN KEY (`lecture_hall_id`) REFERENCES `app_lecturehall` (`id`),
  ADD CONSTRAINT `app_teacherprofile_user_id_a7a599fb_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`);

--
-- Constraints for table `auth_group_permissions`
--
ALTER TABLE `auth_group_permissions`
  ADD CONSTRAINT `auth_group_permissions_group_id_b120cbf9_fk_auth_group_id` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`),
  ADD CONSTRAINT `auth_group_permissio_permission_id_84c5c92e_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`);

--
-- Constraints for table `auth_permission`
--
ALTER TABLE `auth_permission`
  ADD CONSTRAINT `auth_permission_content_type_id_2f476e4b_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`);

--
-- Constraints for table `auth_user_groups`
--
ALTER TABLE `auth_user_groups`
  ADD CONSTRAINT `auth_user_groups_group_id_97559544_fk_auth_group_id` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`),
  ADD CONSTRAINT `auth_user_groups_user_id_6a12ed8b_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`);

--
-- Constraints for table `auth_user_user_permissions`
--
ALTER TABLE `auth_user_user_permissions`
  ADD CONSTRAINT `auth_user_user_permissions_user_id_a95ead1b_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`),
  ADD CONSTRAINT `auth_user_user_permi_permission_id_1fbb5f2c_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`);

--
-- Constraints for table `django_admin_log`
--
ALTER TABLE `django_admin_log`
  ADD CONSTRAINT `django_admin_log_content_type_id_c4bce8eb_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`),
  ADD CONSTRAINT `django_admin_log_user_id_c564eba6_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`);

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
SET FOREIGN_KEY_CHECKS = 1;